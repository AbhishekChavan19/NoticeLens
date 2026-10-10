package com.noticelens.app.ui.components

import android.content.Intent
import android.net.Uri
import android.widget.Toast
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.OpenInNew
import androidx.compose.material.icons.filled.Info
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.util.regex.Pattern

@Composable
fun SectionCard(
    title: String,
    content: Any?,
    icon: ImageVector = Icons.Default.Info,
    fallbackText: String = "Not specified in notice",
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current

    val rawText = when (content) {
        is List<*> -> {
            val items = content.filterNotNull().map { it.toString().trim() }.filter { it.isNotEmpty() }
            if (items.isEmpty()) "" else items.joinToString("\n• ", prefix = "• ")
        }
        is Map<*, *> -> {
            val entries = content.entries.filter { it.value != null && it.value.toString().isNotBlank() }
            if (entries.isEmpty()) "" else entries.joinToString("\n") { "• ${it.key}: ${it.value}" }
        }
        null -> ""
        else -> content.toString().trim()
    }

    val isBlankOrEmpty = rawText.isEmpty() ||
            rawText.equals("N/A", ignoreCase = true) ||
            rawText.equals("None", ignoreCase = true) ||
            rawText.equals("null", ignoreCase = true) ||
            rawText.equals("[]", ignoreCase = true) ||
            rawText.equals("{}", ignoreCase = true)

    val displayText = if (isBlankOrEmpty) fallbackText else rawText
    val isFallback = isBlankOrEmpty

    // Detect if this card or its content contains a Web URL / Portal Link
    val urlPattern = Pattern.compile("(?i)\\b((?:https?://|www\\d{0,3}[.]|[a-z0-9.\\-]+[.][a-z]{2,4}/)(?:[^\\s()<>]+|\\(([^\\s()<>]+|(\\([^\\s()<>]+\\)))*\\))+(?:\\(([^\\s()<>]+|(\\([^\\s()<>]+\\)))*\\)|[^\\s`!()\\[\\]{};:'\".,<>?«»“”‘’]))")
    val matcher = urlPattern.matcher(rawText)
    val extractedUrl = if (matcher.find()) matcher.group(1) else null

    val isPortalOrLinkCard = title.contains("link", ignoreCase = true) ||
            title.contains("portal", ignoreCase = true) ||
            title.contains("website", ignoreCase = true) ||
            title.contains("url", ignoreCase = true)

    val linkToOpen = extractedUrl ?: if (isPortalOrLinkCard && !isFallback) rawText.trim() else null

    Card(
        modifier = modifier
            .fillMaxWidth()
            .padding(vertical = 5.dp),
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(
            containerColor = if (isFallback) {
                MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.35f)
            } else {
                MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.65f)
            }
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 12.dp)
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.padding(bottom = 6.dp)
            ) {
                Icon(
                    imageVector = icon,
                    contentDescription = null,
                    tint = if (isFallback) MaterialTheme.colorScheme.outline else MaterialTheme.colorScheme.primary,
                    modifier = Modifier.size(19.dp)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = title,
                    style = MaterialTheme.typography.titleMedium,
                    color = if (isFallback) MaterialTheme.colorScheme.onSurfaceVariant else MaterialTheme.colorScheme.primary,
                    fontWeight = FontWeight.Bold,
                    fontSize = 15.sp
                )
            }

            Text(
                text = displayText,
                style = MaterialTheme.typography.bodyMedium,
                color = if (isFallback) MaterialTheme.colorScheme.outline else MaterialTheme.colorScheme.onSurface,
                lineHeight = 22.sp,
                fontWeight = if (isFallback) FontWeight.Normal else FontWeight.Medium
            )

            // Direct Redirect Button for Links & Portals
            if (!linkToOpen.isNullOrBlank() && !isFallback) {
                Spacer(modifier = Modifier.height(10.dp))
                Button(
                    onClick = {
                        try {
                            val uriString = if (!linkToOpen.startsWith("http://") && !linkToOpen.startsWith("https://")) {
                                "https://$linkToOpen"
                            } else {
                                linkToOpen
                            }
                            val intent = Intent(Intent.ACTION_VIEW, Uri.parse(uriString))
                            context.startActivity(intent)
                        } catch (e: Exception) {
                            Toast.makeText(context, "Could not open link: ${e.message}", Toast.LENGTH_SHORT).show()
                        }
                    },
                    modifier = Modifier.fillMaxWidth().height(42.dp),
                    shape = RoundedCornerShape(10.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = MaterialTheme.colorScheme.primary
                    )
                ) {
                    Icon(
                        imageVector = Icons.AutoMirrored.Filled.OpenInNew,
                        contentDescription = "Open Link",
                        modifier = Modifier.size(18.dp)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = "Open Portal / Link",
                        fontWeight = FontWeight.Bold,
                        fontSize = 13.sp
                    )
                }
            }
        }
    }
}
