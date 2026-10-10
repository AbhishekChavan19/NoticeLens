package com.noticelens.app.data.model

import com.google.gson.annotations.SerializedName

data class NoticeProcessResponse(
    @SerializedName("success") val success: Boolean = false,
    @SerializedName("error") val error: String? = null,
    @SerializedName("extracted_text") val extractedText: String? = null,
    @SerializedName("language") val language: String? = null,
    @SerializedName("language_confidence") val languageConfidence: Double? = null,
    @SerializedName("category") val category: String? = null,
    @SerializedName("category_confidence") val categoryConfidence: Double? = null,
    @SerializedName("structured_data") val structuredData: Map<String, Any?>? = null,
    @SerializedName("simple_english") val simpleEnglish: Map<String, Any?>? = null,
    @SerializedName("simple_marathi") val simpleMarathi: Map<String, Any?>? = null,
    @SerializedName("model_used") val modelUsed: String? = null
)

sealed class UiState {
    object Idle : UiState()
    data class Loading(val message: String = "Analyzing notice...") : UiState()
    data class Success(val result: NoticeProcessResponse) : UiState()
    data class Error(val errorMessage: String) : UiState()
}

enum class InputMode {
    PDF, CAMERA, GALLERY, TEXT
}

enum class SummaryLanguage {
    ENGLISH, MARATHI
}
