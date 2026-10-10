package com.noticelens.app.ui

import android.Manifest
import android.content.pm.PackageManager
import android.net.Uri
import android.widget.Toast
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Label
import androidx.compose.material.icons.automirrored.filled.OpenInNew
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.core.content.ContextCompat
import coil.compose.AsyncImage
import com.noticelens.app.R
import com.noticelens.app.data.model.InputMode
import com.noticelens.app.data.model.SummaryLanguage
import com.noticelens.app.data.model.UiState
import com.noticelens.app.ui.components.CategoryBadge
import com.noticelens.app.ui.components.SectionCard
import com.noticelens.app.ui.components.ServerConfigDialog

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun NoticeLensScreen(
    viewModel: NoticeLensViewModel,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val clipboardManager = LocalClipboardManager.current
    val isDarkMode by viewModel.isDarkMode.collectAsState()
    val inputMode by viewModel.inputMode.collectAsState()
    val selectedUri by viewModel.selectedUri.collectAsState()
    val cachedLocalFile by viewModel.cachedLocalFile.collectAsState()
    val selectedFileName by viewModel.selectedFileName.collectAsState()
    val textInput by viewModel.textInput.collectAsState()
    val uiState by viewModel.uiState.collectAsState()
    val summaryLanguage by viewModel.summaryLanguage.collectAsState()
    val activeTab by viewModel.activeTab.collectAsState()
    val showSettingsDialog by viewModel.showSettingsDialog.collectAsState()
    val showFullScreenViewer by viewModel.showFullScreenViewer.collectAsState()

    // Real Camera launcher
    val cameraLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.TakePicture()
    ) { success: Boolean ->
        if (success) {
            viewModel.onCameraCaptureSuccess(context)
            Toast.makeText(context, "Notice photo captured!", Toast.LENGTH_SHORT).show()
        }
    }

    // Camera permission requester
    val cameraPermissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission()
    ) { isGranted: Boolean ->
        if (isGranted) {
            try {
                val uri = viewModel.prepareCameraCaptureUri(context)
                cameraLauncher.launch(uri)
            } catch (e: Exception) {
                Toast.makeText(context, "Could not open camera: ${e.message}", Toast.LENGTH_LONG).show()
            }
        } else {
            Toast.makeText(context, "Camera permission is needed to snap notices.", Toast.LENGTH_SHORT).show()
        }
    }

    // PDF picker launcher
    val pdfPickerLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.OpenDocument()
    ) { uri: Uri? ->
        uri?.let { viewModel.setSelectedFile(it, context) }
    }

    // Gallery image picker launcher
    val imagePickerLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.GetContent()
    ) { uri: Uri? ->
        uri?.let { viewModel.setSelectedFile(it, context) }
    }

    // Full-screen Image Viewer Dialog
    if (showFullScreenViewer) {
        Dialog(
            onDismissRequest = { viewModel.setShowFullScreenViewer(false) },
            properties = DialogProperties(usePlatformDefaultWidth = false)
        ) {
            Surface(
                modifier = Modifier.fillMaxSize(),
                color = Color.Black.copy(alpha = 0.95f)
            ) {
                Box(modifier = Modifier.fillMaxSize()) {
                    val imageSource = cachedLocalFile ?: selectedUri
                    AsyncImage(
                        model = imageSource,
                        contentDescription = "Full Notice View",
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(16.dp),
                        contentScale = ContentScale.Fit
                    )

                    // Close button
                    IconButton(
                        onClick = { viewModel.setShowFullScreenViewer(false) },
                        modifier = Modifier
                            .align(Alignment.TopEnd)
                            .padding(16.dp)
                            .background(Color.White.copy(alpha = 0.2f), CircleShape)
                    ) {
                        Icon(
                            Icons.Default.Close,
                            contentDescription = "Close Viewer",
                            tint = Color.White
                        )
                    }

                    // Bottom info label
                    Surface(
                        modifier = Modifier
                            .align(Alignment.BottomCenter)
                            .padding(bottom = 24.dp),
                        shape = RoundedCornerShape(20.dp),
                        color = Color.Black.copy(alpha = 0.6f)
                    ) {
                        Text(
                            text = selectedFileName ?: "Notice Document",
                            color = Color.White,
                            fontSize = 13.sp,
                            modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp)
                        )
                    }
                }
            }
        }
    }

    if (showSettingsDialog) {
        ServerConfigDialog(
            currentUrl = viewModel.currentServerUrl,
            onDismiss = { viewModel.setShowSettingsDialog(false) },
            onSave = { newUrl -> viewModel.updateServerUrl(newUrl) }
        )
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Image(
                            painter = painterResource(id = R.drawable.noticelens_logo),
                            contentDescription = "NoticeLens Logo",
                            modifier = Modifier
                                .size(38.dp)
                                .clip(RoundedCornerShape(10.dp))
                        )
                        Spacer(modifier = Modifier.width(10.dp))
                        Column {
                            Text(
                                text = "NoticeLens",
                                style = MaterialTheme.typography.titleLarge,
                                fontWeight = FontWeight.Bold
                            )
                            Text(
                                text = "Understand • Extract • Take Action",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                                fontSize = 11.sp
                            )
                        }
                    }
                },
                actions = {
                    IconButton(onClick = { viewModel.setShowSettingsDialog(true) }) {
                        Icon(
                            imageVector = Icons.Default.Settings,
                            contentDescription = "Server Settings",
                            tint = MaterialTheme.colorScheme.primary
                        )
                    }
                    IconButton(onClick = { viewModel.toggleDarkMode() }) {
                        Icon(
                            imageVector = if (isDarkMode) Icons.Default.LightMode else Icons.Default.DarkMode,
                            contentDescription = "Toggle Dark Mode",
                            tint = MaterialTheme.colorScheme.primary
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surface
                )
            )
        }
    ) { innerPadding ->
        Column(
            modifier = modifier
                .fillMaxSize()
                .padding(innerPadding)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 16.dp, vertical = 8.dp)
        ) {

            // ═══════════════════════════════════════════════════════════════
            // SIMPLE GUIDE ABOUT HOW TO USE APP (REPLACES OLD DESCRIPTION)
            // ═══════════════════════════════════════════════════════════════
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 14.dp),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.45f)
                ),
                elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(14.dp)
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Icon(
                            imageVector = Icons.Default.MenuBook,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.size(20.dp)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = "How to Use NoticeLens",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.primary
                        )
                    }

                    Spacer(modifier = Modifier.height(10.dp))

                    GuideStepItem(
                        step = "1",
                        title = "Snap or Select",
                        description = "Take a photo of your notice, upload a PDF circular, or paste text."
                    )
                    Spacer(modifier = Modifier.height(6.dp))
                    GuideStepItem(
                        step = "2",
                        title = "Tap Analyze with AI",
                        description = "NoticeLens extracts key dates, fees, and requirements instantly."
                    )
                    Spacer(modifier = Modifier.height(6.dp))
                    GuideStepItem(
                        step = "3",
                        title = "Read in English or मराठी",
                        description = "Get short, high-importance takeaways and open official portal links directly."
                    )
                }
            }

            // ═══════════════════════════════════════════════════════════════
            // INPUT SOURCE SELECTOR TABS
            // ═══════════════════════════════════════════════════════════════
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(14.dp))
                    .background(MaterialTheme.colorScheme.surfaceVariant)
                    .padding(4.dp),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                InputModeTab(
                    icon = Icons.Default.CameraAlt,
                    label = "Camera",
                    selected = inputMode == InputMode.CAMERA,
                    onClick = { viewModel.setInputMode(InputMode.CAMERA) },
                    modifier = Modifier.weight(1f)
                )
                InputModeTab(
                    icon = Icons.Default.PictureAsPdf,
                    label = "PDF",
                    selected = inputMode == InputMode.PDF,
                    onClick = { viewModel.setInputMode(InputMode.PDF) },
                    modifier = Modifier.weight(1f)
                )
                InputModeTab(
                    icon = Icons.Default.Image,
                    label = "Gallery",
                    selected = inputMode == InputMode.GALLERY,
                    onClick = { viewModel.setInputMode(InputMode.GALLERY) },
                    modifier = Modifier.weight(1f)
                )
                InputModeTab(
                    icon = Icons.Default.Edit,
                    label = "Text",
                    selected = inputMode == InputMode.TEXT,
                    onClick = { viewModel.setInputMode(InputMode.TEXT) },
                    modifier = Modifier.weight(1f)
                )
            }

            Spacer(modifier = Modifier.height(12.dp))

            // ═══════════════════════════════════════════════════════════════
            // INPUT & PREVIEW CARD
            // ═══════════════════════════════════════════════════════════════
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.surface
                ),
                elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(14.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    when (inputMode) {
                        InputMode.CAMERA -> {
                            Button(
                                onClick = {
                                    val hasPermission = ContextCompat.checkSelfPermission(
                                        context,
                                        Manifest.permission.CAMERA
                                    ) == PackageManager.PERMISSION_GRANTED

                                    if (hasPermission) {
                                        try {
                                            val uri = viewModel.prepareCameraCaptureUri(context)
                                            cameraLauncher.launch(uri)
                                        } catch (e: Exception) {
                                            Toast.makeText(context, "Camera error: ${e.message}", Toast.LENGTH_LONG).show()
                                        }
                                    } else {
                                        cameraPermissionLauncher.launch(Manifest.permission.CAMERA)
                                    }
                                },
                                modifier = Modifier.fillMaxWidth().height(48.dp),
                                shape = RoundedCornerShape(12.dp)
                            ) {
                                Icon(Icons.Default.PhotoCamera, contentDescription = null)
                                Spacer(modifier = Modifier.width(8.dp))
                                Text(if (selectedUri != null) "Retake Photo" else "Snap Notice with Camera")
                            }
                        }

                        InputMode.PDF -> {
                            OutlinedButton(
                                onClick = { pdfPickerLauncher.launch(arrayOf("application/pdf")) },
                                modifier = Modifier.fillMaxWidth().height(48.dp),
                                shape = RoundedCornerShape(12.dp)
                            ) {
                                Icon(Icons.Default.UploadFile, contentDescription = null)
                                Spacer(modifier = Modifier.width(8.dp))
                                Text(if (selectedUri != null) "Choose Another PDF" else "Upload PDF Circular")
                            }
                        }

                        InputMode.GALLERY -> {
                            OutlinedButton(
                                onClick = { imagePickerLauncher.launch("image/*") },
                                modifier = Modifier.fillMaxWidth().height(48.dp),
                                shape = RoundedCornerShape(12.dp)
                            ) {
                                Icon(Icons.Default.Image, contentDescription = null)
                                Spacer(modifier = Modifier.width(8.dp))
                                Text(if (selectedUri != null) "Choose Another Image" else "Browse Gallery")
                            }
                        }

                        InputMode.TEXT -> {
                            OutlinedTextField(
                                value = textInput,
                                onValueChange = { viewModel.setTextInput(it) },
                                label = { Text("Paste or type notice text here...") },
                                supportingText = {
                                    Text("${textInput.length} characters")
                                },
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .heightIn(min = 120.dp, max = 220.dp),
                                shape = RoundedCornerShape(12.dp)
                            )
                        }
                    }

                    // ═══════════════════════════════════════════════════════════
                    // UPLOADED NOTICE PREVIEW CARD (CLICK TO OPEN)
                    // ═══════════════════════════════════════════════════════════
                    val hasFile = selectedUri != null || cachedLocalFile != null

                    if (inputMode != InputMode.TEXT && hasFile) {
                        Spacer(modifier = Modifier.height(14.dp))
                        HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
                        Spacer(modifier = Modifier.height(10.dp))

                        val isImage = inputMode == InputMode.CAMERA || inputMode == InputMode.GALLERY
                        val previewSource = cachedLocalFile ?: selectedUri

                        Column(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clip(RoundedCornerShape(14.dp))
                                .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f))
                                .clickable { viewModel.openUploadedNotice(context) }
                                .padding(12.dp)
                        ) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Icon(
                                        imageVector = if (isImage) Icons.Default.Image else Icons.Default.PictureAsPdf,
                                        contentDescription = null,
                                        tint = MaterialTheme.colorScheme.primary,
                                        modifier = Modifier.size(18.dp)
                                    )
                                    Spacer(modifier = Modifier.width(6.dp))
                                    Text(
                                        text = if (isImage) "Notice Photo Preview" else "PDF Document Preview",
                                        style = MaterialTheme.typography.titleSmall,
                                        fontWeight = FontWeight.Bold,
                                        color = MaterialTheme.colorScheme.primary
                                    )
                                }

                                Row {
                                    // Open notice icon
                                    IconButton(
                                        onClick = { viewModel.openUploadedNotice(context) },
                                        modifier = Modifier.size(28.dp)
                                    ) {
                                        Icon(
                                            Icons.AutoMirrored.Filled.OpenInNew,
                                            contentDescription = "Open notice",
                                            tint = MaterialTheme.colorScheme.primary,
                                            modifier = Modifier.size(18.dp)
                                        )
                                    }
                                    Spacer(modifier = Modifier.width(6.dp))
                                    // Remove notice icon
                                    IconButton(
                                        onClick = { viewModel.clearSelectedFile() },
                                        modifier = Modifier.size(28.dp)
                                    ) {
                                        Icon(
                                            Icons.Default.Close,
                                            contentDescription = "Remove file",
                                            tint = MaterialTheme.colorScheme.error,
                                            modifier = Modifier.size(18.dp)
                                        )
                                    }
                                }
                            }

                            Spacer(modifier = Modifier.height(8.dp))

                            if (isImage) {
                                Box(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .height(180.dp)
                                        .clip(RoundedCornerShape(10.dp))
                                        .border(1.dp, MaterialTheme.colorScheme.outlineVariant, RoundedCornerShape(10.dp))
                                ) {
                                    AsyncImage(
                                        model = previewSource,
                                        contentDescription = "Notice Photo Thumbnail",
                                        modifier = Modifier.fillMaxSize(),
                                        contentScale = ContentScale.Crop
                                    )

                                    // Tap to expand overlay badge
                                    Surface(
                                        shape = RoundedCornerShape(12.dp),
                                        color = Color.Black.copy(alpha = 0.65f),
                                        modifier = Modifier
                                            .align(Alignment.BottomEnd)
                                            .padding(8.dp)
                                    ) {
                                        Row(
                                            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                                            verticalAlignment = Alignment.CenterVertically
                                        ) {
                                            Icon(
                                                Icons.Default.ZoomIn,
                                                contentDescription = null,
                                                tint = Color.White,
                                                modifier = Modifier.size(14.dp)
                                            )
                                            Spacer(modifier = Modifier.width(4.dp))
                                            Text(
                                                text = "Tap to open full notice",
                                                color = Color.White,
                                                fontSize = 11.sp,
                                                fontWeight = FontWeight.SemiBold
                                            )
                                        }
                                    }
                                }
                            } else {
                                // PDF tap to open card
                                Row(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .clip(RoundedCornerShape(10.dp))
                                        .background(MaterialTheme.colorScheme.surface)
                                        .padding(12.dp),
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Surface(
                                        shape = RoundedCornerShape(8.dp),
                                        color = MaterialTheme.colorScheme.primaryContainer,
                                        modifier = Modifier.size(44.dp)
                                    ) {
                                        Box(contentAlignment = Alignment.Center) {
                                            Icon(
                                                Icons.Default.PictureAsPdf,
                                                contentDescription = null,
                                                tint = MaterialTheme.colorScheme.primary
                                            )
                                        }
                                    }
                                    Spacer(modifier = Modifier.width(12.dp))
                                    Column(modifier = Modifier.weight(1f)) {
                                        Text(
                                            text = selectedFileName ?: "Notice Document.pdf",
                                            style = MaterialTheme.typography.bodyMedium,
                                            fontWeight = FontWeight.Bold,
                                            maxLines = 1
                                        )
                                        Text(
                                            text = "📄 Tap to open PDF circular",
                                            style = MaterialTheme.typography.bodySmall,
                                            color = MaterialTheme.colorScheme.primary,
                                            fontWeight = FontWeight.SemiBold
                                        )
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(14.dp))

            // ═══════════════════════════════════════════════════════════════
            // ANALYZE BUTTON
            // ═══════════════════════════════════════════════════════════════
            Button(
                onClick = { viewModel.processNotice(context) },
                enabled = uiState !is UiState.Loading && (selectedUri != null || cachedLocalFile != null || textInput.isNotBlank()),
                modifier = Modifier
                    .fillMaxWidth()
                    .height(52.dp),
                shape = RoundedCornerShape(14.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = MaterialTheme.colorScheme.primary
                )
            ) {
                if (uiState is UiState.Loading) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(24.dp),
                        color = MaterialTheme.colorScheme.onPrimary,
                        strokeWidth = 2.dp
                    )
                    Spacer(modifier = Modifier.width(10.dp))
                    Text("Analyzing Notice...", fontSize = 16.sp)
                } else {
                    Icon(Icons.Default.AutoAwesome, contentDescription = null)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Analyze Notice with AI", fontSize = 16.sp, fontWeight = FontWeight.Bold)
                }
            }

            Spacer(modifier = Modifier.height(14.dp))

            // Error Message Display
            if (uiState is UiState.Error) {
                val errorMsg = (uiState as UiState.Error).errorMessage
                Card(
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer),
                    shape = RoundedCornerShape(12.dp),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Row(
                        modifier = Modifier.padding(14.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(
                            imageVector = Icons.Default.ErrorOutline,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.error
                        )
                        Spacer(modifier = Modifier.width(10.dp))
                        Text(
                            text = errorMsg,
                            color = MaterialTheme.colorScheme.onErrorContainer,
                            style = MaterialTheme.typography.bodyMedium
                        )
                    }
                }
            }

            // ═══════════════════════════════════════════════════════════════
            // RESULTS SECTION
            // ═══════════════════════════════════════════════════════════════
            if (uiState is UiState.Success) {
                val response = (uiState as UiState.Success).result

                Spacer(modifier = Modifier.height(6.dp))

                // Overview Header Card
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.surface
                    ),
                    elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = "Notice Analysis",
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.Bold
                            )
                            IconButton(onClick = { viewModel.resetState() }) {
                                Icon(Icons.Default.Refresh, contentDescription = "Clear & New Notice")
                            }
                        }

                        Spacer(modifier = Modifier.height(8.dp))

                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            CategoryBadge(
                                category = response.category ?: "General",
                                confidence = response.categoryConfidence
                            )

                            Surface(
                                shape = RoundedCornerShape(16.dp),
                                color = MaterialTheme.colorScheme.secondaryContainer,
                                modifier = Modifier.padding(vertical = 4.dp)
                            ) {
                                Text(
                                    text = "🌐 ${response.language ?: "English"}",
                                    modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
                                    fontSize = 12.sp,
                                    fontWeight = FontWeight.SemiBold,
                                    color = MaterialTheme.colorScheme.onSecondaryContainer
                                )
                            }
                        }
                    }
                }

                Spacer(modifier = Modifier.height(14.dp))

                // Result Tabs: Summary, Structured Data, Raw Text
                TabRow(
                    selectedTabIndex = activeTab,
                    containerColor = MaterialTheme.colorScheme.surfaceVariant,
                    modifier = Modifier.clip(RoundedCornerShape(12.dp))
                ) {
                    Tab(
                        selected = activeTab == 0,
                        onClick = { viewModel.setActiveTab(0) },
                        text = { Text("Summary", fontWeight = FontWeight.Bold) }
                    )
                    Tab(
                        selected = activeTab == 1,
                        onClick = { viewModel.setActiveTab(1) },
                        text = { Text("Details", fontWeight = FontWeight.Bold) }
                    )
                    Tab(
                        selected = activeTab == 2,
                        onClick = { viewModel.setActiveTab(2) },
                        text = { Text("Raw Text", fontWeight = FontWeight.Bold) }
                    )
                }

                Spacer(modifier = Modifier.height(12.dp))

                when (activeTab) {
                    // TAB 0: Actionable Student Summary (English & Marathi Toggle)
                    0 -> {
                        // Language Toggle: English vs Marathi
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(vertical = 4.dp),
                            horizontalArrangement = Arrangement.Center
                        ) {
                            FilterChip(
                                selected = summaryLanguage == SummaryLanguage.ENGLISH,
                                onClick = { viewModel.setSummaryLanguage(SummaryLanguage.ENGLISH) },
                                label = { Text("🇬🇧 Simple English") },
                                leadingIcon = {
                                    if (summaryLanguage == SummaryLanguage.ENGLISH) {
                                        Icon(Icons.Default.Check, contentDescription = null, modifier = Modifier.size(16.dp))
                                    }
                                }
                            )
                            Spacer(modifier = Modifier.width(10.dp))
                            FilterChip(
                                selected = summaryLanguage == SummaryLanguage.MARATHI,
                                onClick = { viewModel.setSummaryLanguage(SummaryLanguage.MARATHI) },
                                label = { Text("🇮🇳 सोपे मराठी") },
                                leadingIcon = {
                                    if (summaryLanguage == SummaryLanguage.MARATHI) {
                                        Icon(Icons.Default.Check, contentDescription = null, modifier = Modifier.size(16.dp))
                                    }
                                }
                            )
                        }

                        Spacer(modifier = Modifier.height(8.dp))

                        if (summaryLanguage == SummaryLanguage.ENGLISH) {
                            val en = response.simpleEnglish ?: emptyMap()

                            // Key Essence / Importance Card (Prominent & Short)
                            val aboutNotice = en["what_is_this_notice_about"] ?: en["What is this notice about?"] ?: en["summary"] ?: en["notice_about"]
                            Card(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(vertical = 6.dp),
                                shape = RoundedCornerShape(14.dp),
                                colors = CardDefaults.cardColors(
                                    containerColor = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.55f)
                                )
                            ) {
                                Column(modifier = Modifier.padding(16.dp)) {
                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        Icon(
                                            Icons.Default.Star,
                                            contentDescription = null,
                                            tint = MaterialTheme.colorScheme.primary,
                                            modifier = Modifier.size(20.dp)
                                        )
                                        Spacer(modifier = Modifier.width(8.dp))
                                        Text(
                                            text = "What is this notice about? (Core Importance)",
                                            style = MaterialTheme.typography.titleMedium,
                                            fontWeight = FontWeight.Bold,
                                            color = MaterialTheme.colorScheme.primary
                                        )
                                    }
                                    Spacer(modifier = Modifier.height(6.dp))
                                    Text(
                                        text = aboutNotice?.toString() ?: "Important official circular for students.",
                                        style = MaterialTheme.typography.bodyLarge,
                                        fontWeight = FontWeight.Medium,
                                        lineHeight = 22.sp,
                                        color = MaterialTheme.colorScheme.onSurface
                                    )
                                }
                            }

                            SectionCard(
                                title = "Who is it for?",
                                content = en["who_is_it_for"] ?: en["Who is it for?"] ?: en["target_audience"],
                                icon = Icons.Default.Groups,
                                fallbackText = "All students mentioned in the notice."
                            )
                            SectionCard(
                                title = "What do I need to do?",
                                content = en["what_do_i_need_to_do"] ?: en["What do I need to do?"] ?: en["action_items"],
                                icon = Icons.Default.CheckCircle,
                                fallbackText = "No specific action required. For information only."
                            )
                            SectionCard(
                                title = "Deadline",
                                content = en["deadline"] ?: en["Deadline"],
                                icon = Icons.Default.EventBusy,
                                fallbackText = "No deadline mentioned in the notice."
                            )
                            SectionCard(
                                title = "Important dates",
                                content = en["important_dates"] ?: en["Important dates"] ?: en["dates"],
                                icon = Icons.Default.CalendarMonth,
                                fallbackText = "No specific dates mentioned."
                            )
                            SectionCard(
                                title = "Documents required",
                                content = en["documents_required"] ?: en["Documents required"] ?: en["documents"],
                                icon = Icons.Default.Folder,
                                fallbackText = "No documents required."
                            )
                            SectionCard(
                                title = "Fees",
                                content = en["fees"] ?: en["Fees"] ?: en["fee"],
                                icon = Icons.Default.Payments,
                                fallbackText = "No fees mentioned (Free)."
                            )
                            SectionCard(
                                title = "Eligibility",
                                content = en["eligibility"] ?: en["Eligibility"],
                                icon = Icons.Default.Verified,
                                fallbackText = "Applicable to all eligible students."
                            )
                            SectionCard(
                                title = "Important note",
                                content = en["important_note"] ?: en["Important note"] ?: en["notes"],
                                icon = Icons.Default.PriorityHigh,
                                fallbackText = "Please follow college guidelines."
                            )
                        } else {
                            val mr = response.simpleMarathi ?: emptyMap()

                            // Key Essence / Importance Card (Marathi)
                            val aboutNoticeMr = mr["हा_नोटीस_कशाबद्दल_आहे"] ?: mr["हा नोटीस कशाबद्दल आहे?"] ?: mr["notice_about"] ?: mr["summary"]
                            Card(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(vertical = 6.dp),
                                shape = RoundedCornerShape(14.dp),
                                colors = CardDefaults.cardColors(
                                    containerColor = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.55f)
                                )
                            ) {
                                Column(modifier = Modifier.padding(16.dp)) {
                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        Icon(
                                            Icons.Default.Star,
                                            contentDescription = null,
                                            tint = MaterialTheme.colorScheme.primary,
                                            modifier = Modifier.size(20.dp)
                                        )
                                        Spacer(modifier = Modifier.width(8.dp))
                                        Text(
                                            text = "हा नोटीस कशाबद्दल आहे? (मुख्य महत्त्व)",
                                            style = MaterialTheme.typography.titleMedium,
                                            fontWeight = FontWeight.Bold,
                                            color = MaterialTheme.colorScheme.primary
                                        )
                                    }
                                    Spacer(modifier = Modifier.height(6.dp))
                                    Text(
                                        text = aboutNoticeMr?.toString() ?: "विद्यार्थ्यांसाठी महत्त्वाची नोटीस.",
                                        style = MaterialTheme.typography.bodyLarge,
                                        fontWeight = FontWeight.Medium,
                                        lineHeight = 22.sp,
                                        color = MaterialTheme.colorScheme.onSurface
                                    )
                                }
                            }

                            SectionCard(
                                title = "कोणासाठी आहे?",
                                content = mr["कोणासाठी_आहे"] ?: mr["कोणासाठी आहे?"] ?: mr["who_is_it_for"] ?: mr["target_audience"],
                                icon = Icons.Default.Groups,
                                fallbackText = "सर्व संबंधित विद्यार्थ्यांसाठी लागू."
                            )
                            SectionCard(
                                title = "मला काय करावे लागेल?",
                                content = mr["मला_काय_करावे_लागेल"] ?: mr["मला काय करावे लागेल?"] ?: mr["what_to_do"] ?: mr["action_items"],
                                icon = Icons.Default.CheckCircle,
                                fallbackText = "कोणतीही कृती आवश्यक नाही. केवळ माहितीसाठी."
                            )
                            SectionCard(
                                title = "अंतिम तारीख",
                                content = mr["अंतिम_तारीख"] ?: mr["अंतिम तारीख"] ?: mr["deadline"],
                                icon = Icons.Default.EventBusy,
                                fallbackText = "कोणतीही अंतिम तारीख नमूद केलेली नाही."
                            )
                            SectionCard(
                                title = "महत्त्वाच्या तारखा",
                                content = mr["महत्त्वाच्या_तारखा"] ?: mr["महत्त्वाच्या तारखा"] ?: mr["important_dates"],
                                icon = Icons.Default.CalendarMonth,
                                fallbackText = "कोणत्याही विशेष तारखा नमूद केलेल्या नाहीत."
                            )
                            SectionCard(
                                title = "आवश्यक कागदपत्रे",
                                content = mr["आवश्यक_कागदपत्रे"] ?: mr["आवश्यक कागदपत्रे"] ?: mr["documents_required"],
                                icon = Icons.Default.Folder,
                                fallbackText = "कोणत्याही कागदपत्रांची आवश्यकता नाही."
                            )
                            SectionCard(
                                title = "फी",
                                content = mr["फी"] ?: mr["fees"] ?: mr["fee"],
                                icon = Icons.Default.Payments,
                                fallbackText = "कोणतीही फी नमूद केलेली नाही (मोफत)."
                            )
                            SectionCard(
                                title = "पात्रता",
                                content = mr["पात्रता"] ?: mr["eligibility"],
                                icon = Icons.Default.Verified,
                                fallbackText = "सर्व संबंधित विद्यार्थ्यांसाठी लागू."
                            )
                            SectionCard(
                                title = "महत्त्वाची सूचना",
                                content = mr["महत्त्वाची_सूचना"] ?: mr["महत्त्वाची सूचना"] ?: mr["important_note"],
                                icon = Icons.Default.PriorityHigh,
                                fallbackText = "कॉलेजच्या नियमांचे पालन करा."
                            )
                        }
                    }

                    // TAB 1: Structured Information Details (With Direct Portal / Link Redirection)
                    1 -> {
                        val structured = response.structuredData ?: emptyMap()
                        if (structured.isEmpty()) {
                            Text("No structured details available.", style = MaterialTheme.typography.bodyMedium)
                        } else {
                            structured.forEach { (key, value) ->
                                SectionCard(
                                    title = key.replace('_', ' ').replaceFirstChar { it.uppercase() },
                                    content = value,
                                    icon = Icons.AutoMirrored.Filled.Label,
                                    fallbackText = "Not specified"
                                )
                            }
                        }
                    }

                    // TAB 2: Raw Extracted Text
                    2 -> {
                        val rawText = response.extractedText ?: "No text extracted."
                        Card(
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(14.dp),
                            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
                        ) {
                            Column(modifier = Modifier.padding(14.dp)) {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Text(
                                        text = "Extracted Text (${rawText.length} characters)",
                                        style = MaterialTheme.typography.titleSmall,
                                        fontWeight = FontWeight.Bold
                                    )
                                    IconButton(
                                        onClick = {
                                            clipboardManager.setText(AnnotatedString(rawText))
                                            Toast.makeText(context, "Text copied to clipboard", Toast.LENGTH_SHORT).show()
                                        }
                                    ) {
                                        Icon(Icons.Default.ContentCopy, contentDescription = "Copy text")
                                    }
                                }
                                Spacer(modifier = Modifier.height(8.dp))
                                Text(
                                    text = rawText,
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(30.dp))
        }
    }
}

@Composable
fun GuideStepItem(
    step: String,
    title: String,
    description: String
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.Top
    ) {
        Surface(
            shape = CircleShape,
            color = MaterialTheme.colorScheme.primary,
            modifier = Modifier.size(20.dp)
        ) {
            Box(contentAlignment = Alignment.Center) {
                Text(
                    text = step,
                    color = MaterialTheme.colorScheme.onPrimary,
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Bold
                )
            }
        }
        Spacer(modifier = Modifier.width(10.dp))
        Column {
            Text(
                text = title,
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onSurface
            )
            Text(
                text = description,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                lineHeight = 16.sp
            )
        }
    }
}

@Composable
fun InputModeTab(
    icon: ImageVector,
    label: String,
    selected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    val bgColor = if (selected) MaterialTheme.colorScheme.surface else Color.Transparent
    val contentColor = if (selected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant

    Box(
        modifier = modifier
            .clip(RoundedCornerShape(10.dp))
            .background(bgColor)
            .clickable(onClick = onClick)
            .padding(vertical = 10.dp),
        contentAlignment = Alignment.Center
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Icon(
                imageVector = icon,
                contentDescription = label,
                tint = contentColor,
                modifier = Modifier.size(22.dp)
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = label,
                fontSize = 11.sp,
                fontWeight = if (selected) FontWeight.Bold else FontWeight.Normal,
                color = contentColor
            )
        }
    }
}
