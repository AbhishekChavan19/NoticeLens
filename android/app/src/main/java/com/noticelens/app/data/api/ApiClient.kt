package com.noticelens.app.data.api

import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

object ApiClient {
    // Default URL pointing to Railway cloud backend
    private var currentBaseUrl: String = "https://noticelens-production.up.railway.app/"

    private val loggingInterceptor = HttpLoggingInterceptor().apply {
        level = HttpLoggingInterceptor.Level.BODY
    }

    private val okHttpClient = OkHttpClient.Builder()
        .addInterceptor(loggingInterceptor)
        .connectTimeout(120, TimeUnit.SECONDS)
        .readTimeout(120, TimeUnit.SECONDS)
        .writeTimeout(120, TimeUnit.SECONDS)
        .retryOnConnectionFailure(true)
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
