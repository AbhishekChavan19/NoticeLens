package com.noticelens.app.data.api

import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

object ApiClient {
    // Default URL for Android Emulator talking to host PC localhost:8000
    private var currentBaseUrl: String = "http://10.0.2.2:8000/"

    private val loggingInterceptor = HttpLoggingInterceptor().apply {
        level = HttpLoggingInterceptor.Level.BODY
    }

    private val okHttpClient = OkHttpClient.Builder()
        .addInterceptor(loggingInterceptor)
        .connectTimeout(60, TimeUnit.SECONDS)
        .readTimeout(90, TimeUnit.SECONDS)
        .writeTimeout(90, TimeUnit.SECONDS)
        .build()

    private var retrofit: Retrofit = buildRetrofit(currentBaseUrl)
    var service: NoticeLensApiService = retrofit.create(NoticeLensApiService::class.java)
        private set

    private fun buildRetrofit(url: String): Retrofit {
        val sanitized = if (url.endsWith("/")) url else "$url/"
        return Retrofit.Builder()
            .baseUrl(sanitized)
            .client(okHttpClient)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
    }

    fun updateBaseUrl(newUrl: String) {
        val trimmed = newUrl.trim()
        if (trimmed.isNotEmpty() && trimmed != currentBaseUrl) {
            currentBaseUrl = if (trimmed.endsWith("/")) trimmed else "$trimmed/"
            retrofit = buildRetrofit(currentBaseUrl)
            service = retrofit.create(NoticeLensApiService::class.java)
        }
    }

    fun getBaseUrl(): String = currentBaseUrl
}
