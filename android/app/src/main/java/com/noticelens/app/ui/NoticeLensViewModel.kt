package com.noticelens.app.ui

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.provider.OpenableColumns
import android.widget.Toast
import androidx.core.content.FileProvider
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.noticelens.app.data.api.ApiClient
import com.noticelens.app.data.model.InputMode
import com.noticelens.app.data.model.SummaryLanguage
import com.noticelens.app.data.model.UiState
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.File
import java.io.FileOutputStream
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class NoticeLensViewModel : ViewModel() {

    private val _isDarkMode = MutableStateFlow(false)
    val isDarkMode: StateFlow<Boolean> = _isDarkMode.asStateFlow()

    private val _inputMode = MutableStateFlow(InputMode.CAMERA)
    val inputMode: StateFlow<InputMode> = _inputMode.asStateFlow()

    private val _selectedUri = MutableStateFlow<Uri?>(null)
    val selectedUri: StateFlow<Uri?> = _selectedUri.asStateFlow()

    private val _cachedLocalFile = MutableStateFlow<File?>(null)
    val cachedLocalFile: StateFlow<File?> = _cachedLocalFile.asStateFlow()

    private val _selectedFileName = MutableStateFlow<String?>(null)
    val selectedFileName: StateFlow<String?> = _selectedFileName.asStateFlow()

    private val _textInput = MutableStateFlow("")
    val textInput: StateFlow<String> = _textInput.asStateFlow()

    private val _uiState = MutableStateFlow<UiState>(UiState.Idle)
    val uiState: StateFlow<UiState> = _uiState.asStateFlow()

    private val _summaryLanguage = MutableStateFlow(SummaryLanguage.ENGLISH)
    val summaryLanguage: StateFlow<SummaryLanguage> = _summaryLanguage.asStateFlow()

    private val _activeTab = MutableStateFlow(0) // 0: Summary, 1: Structured, 2: Raw Text
    val activeTab: StateFlow<Int> = _activeTab.asStateFlow()

    private val _showSettingsDialog = MutableStateFlow(false)
    val showSettingsDialog: StateFlow<Boolean> = _showSettingsDialog.asStateFlow()

    private val _showFullScreenViewer = MutableStateFlow(false)
    val showFullScreenViewer: StateFlow<Boolean> = _showFullScreenViewer.asStateFlow()

    var pendingCameraUri: Uri? = null
        private set

    val currentServerUrl: String get() = ApiClient.getBaseUrl()

    fun toggleDarkMode() {
        _isDarkMode.value = !_isDarkMode.value
    }

    fun setInputMode(mode: InputMode) {
        _inputMode.value = mode
    }

    fun setSummaryLanguage(lang: SummaryLanguage) {
        _summaryLanguage.value = lang
    }

    fun setActiveTab(index: Int) {
        _activeTab.value = index
    }

    fun setShowSettingsDialog(show: Boolean) {
        _showSettingsDialog.value = show
    }

    fun setShowFullScreenViewer(show: Boolean) {
        _showFullScreenViewer.value = show
    }

    fun updateServerUrl(newUrl: String) {
        ApiClient.updateBaseUrl(newUrl)
        _showSettingsDialog.value = false
    }

    fun setTextInput(text: String) {
        _textInput.value = text
    }

    fun setSelectedFile(uri: Uri?, context: Context) {
        _selectedUri.value = uri
        if (uri != null) {
            _selectedFileName.value = getFileNameFromUri(context, uri)
            viewModelScope.launch {
                val cached = withContext(Dispatchers.IO) {
                    copyUriToTempFile(context, uri)
                }
                _cachedLocalFile.value = cached
            }
        } else {
            _selectedFileName.value = null
            _cachedLocalFile.value = null
        }
    }

    fun clearSelectedFile() {
        _selectedUri.value = null
        _cachedLocalFile.value = null
        _selectedFileName.value = null
        pendingCameraUri = null
    }

    fun prepareCameraCaptureUri(context: Context): Uri {
        val timeStamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.getDefault()).format(Date())
        val imageFile = File(context.cacheDir, "NOTICE_PHOTO_${timeStamp}.jpg")
        val uri = FileProvider.getUriForFile(
            context,
            "${context.packageName}.provider",
            imageFile
        )
        pendingCameraUri = uri
        return uri
    }

    fun onCameraCaptureSuccess(context: Context) {
        pendingCameraUri?.let { uri ->
            setSelectedFile(uri, context)
        }
    }

    fun openUploadedNotice(context: Context) {
        val file = _cachedLocalFile.value
        val uri = _selectedUri.value

        if (file != null && file.exists()) {
            val isPdf = file.name.endsWith(".pdf", ignoreCase = true)
            if (isPdf) {
                try {
                    val contentUri = FileProvider.getUriForFile(
                        context,
                        "${context.packageName}.provider",
                        file
                    )
                    val intent = Intent(Intent.ACTION_VIEW).apply {
                        setDataAndType(contentUri, "application/pdf")
                        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                        addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                    }
                    context.startActivity(intent)
                } catch (e: Exception) {
                    Toast.makeText(context, "No PDF viewer app found on device.", Toast.LENGTH_LONG).show()
                }
            } else {
                // For images, toggle in-app full screen viewer
                _showFullScreenViewer.value = true
            }
        } else if (uri != null) {
            _showFullScreenViewer.value = true
        } else {
            Toast.makeText(context, "No notice file available to open.", Toast.LENGTH_SHORT).show()
        }
    }

    private fun getFileNameFromUri(context: Context, uri: Uri): String {
        var name = "notice_file"
        try {
            context.contentResolver.query(uri, null, null, null, null)?.use { cursor ->
                val nameIndex = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                if (nameIndex != -1 && cursor.moveToFirst()) {
                    name = cursor.getString(nameIndex) ?: name
                }
            }
        } catch (_: Exception) {
            name = uri.lastPathSegment ?: "notice_image.jpg"
        }
        return name
    }

    fun processNotice(context: Context) {
        viewModelScope.launch {
            _uiState.value = UiState.Loading("Processing notice through NoticeLens AI...")

            try {
                val mode = _inputMode.value

                var filePart: MultipartBody.Part? = null
                var textPart: okhttp3.RequestBody? = null

                if (mode == InputMode.TEXT) {
                    val text = _textInput.value.trim()
                    if (text.isEmpty()) {
                        _uiState.value = UiState.Error("Please enter or paste notice text first.")
                        return@launch
                    }
                    textPart = text.toRequestBody("text/plain".toMediaTypeOrNull())
                } else {
                    val localFile = _cachedLocalFile.value ?: run {
                        val uri = _selectedUri.value ?: run {
                            _uiState.value = UiState.Error("Please select a file or take a picture first.")
                            return@launch
                        }
                        copyUriToTempFile(context, uri)
                    }

                    if (localFile == null || !localFile.exists()) {
                        _uiState.value = UiState.Error("Failed to read notice file.")
                        return@launch
                    }

                    val uri = _selectedUri.value
                    val mimeType = if (uri != null) {
                        context.contentResolver.getType(uri) ?: "application/octet-stream"
                    } else if (localFile.name.endsWith(".pdf", ignoreCase = true)) {
                        "application/pdf"
                    } else {
                        "image/jpeg"
                    }

                    val requestBody = localFile.asRequestBody(mimeType.toMediaTypeOrNull())
                    filePart = MultipartBody.Part.createFormData("file", localFile.name, requestBody)
                }

                val providerPart = "groq".toRequestBody("text/plain".toMediaTypeOrNull())

                val response = ApiClient.service.processNotice(
                    file = filePart,
                    textInput = textPart,
                    provider = providerPart,
                    apiKey = null
                )

                if (response.isSuccessful && response.body() != null) {
                    val result = response.body()!!
                    if (result.success) {
                        _uiState.value = UiState.Success(result)
                    } else {
                        _uiState.value = UiState.Error(result.error ?: "Analysis failed.")
                    }
                } else {
                    val errBody = response.errorBody()?.string()
                    _uiState.value = UiState.Error("Server error (${response.code()}): $errBody")
                }

            } catch (e: Exception) {
                _uiState.value = UiState.Error("Connection error: ${e.localizedMessage ?: e.message}\nEnsure backend is running and URL is reachable.")
            }
        }
    }

    private fun copyUriToTempFile(context: Context, uri: Uri): File? {
        return try {
            val fileName = getFileNameFromUri(context, uri)
            val extension = if (fileName.contains(".")) fileName.substringAfterLast(".") else "tmp"
            val tempFile = File.createTempFile("notice_cache_", ".$extension", context.cacheDir)
            context.contentResolver.openInputStream(uri)?.use { inputStream ->
                FileOutputStream(tempFile).use { outputStream ->
                    inputStream.copyTo(outputStream)
                }
            }
            tempFile
        } catch (e: Exception) {
            null
        }
    }

    fun resetState() {
        _uiState.value = UiState.Idle
        _selectedUri.value = null
        _cachedLocalFile.value = null
        _selectedFileName.value = null
        _textInput.value = ""
        pendingCameraUri = null
        _showFullScreenViewer.value = false
    }
}
