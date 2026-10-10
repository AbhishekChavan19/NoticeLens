package com.noticelens.app.data.api

import com.noticelens.app.data.model.NoticeProcessResponse
import okhttp3.MultipartBody
import okhttp3.RequestBody
import retrofit2.Response
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part

interface NoticeLensApiService {

    @Multipart
    @POST("api/v1/process")
    suspend fun processNotice(
        @Part file: MultipartBody.Part? = null,
        @Part("text_input") textInput: RequestBody? = null,
        @Part("provider") provider: RequestBody? = null,
        @Part("api_key") apiKey: RequestBody? = null
    ): Response<NoticeProcessResponse>
}
