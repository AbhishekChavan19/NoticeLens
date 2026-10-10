package com.noticelens.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import com.noticelens.app.ui.NoticeLensScreen
import com.noticelens.app.ui.NoticeLensViewModel
import com.noticelens.app.ui.theme.NoticeLensTheme

class MainActivity : ComponentActivity() {

    private val viewModel: NoticeLensViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        setContent {
            val isDarkMode by viewModel.isDarkMode.collectAsState()

            NoticeLensTheme(darkTheme = isDarkMode) {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = androidx.compose.material3.MaterialTheme.colorScheme.background
                ) {
                    NoticeLensScreen(viewModel = viewModel)
                }
            }
        }
    }
}
