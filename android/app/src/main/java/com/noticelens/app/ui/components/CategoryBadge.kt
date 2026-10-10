package com.noticelens.app.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.noticelens.app.ui.theme.*

@Composable
fun CategoryBadge(
    category: String,
    confidence: Double? = null,
    modifier: Modifier = Modifier
) {
    val (badgeBg, textColor) = when (category.lowercase()) {
        "examination", "exam" -> Pair(CategoryExam.copy(alpha = 0.15f), CategoryExam)
        "academics", "academic" -> Pair(CategoryAcademic.copy(alpha = 0.15f), CategoryAcademic)
        "fees" -> Pair(CategoryFees.copy(alpha = 0.15f), CategoryFees)
        "scholarship" -> Pair(CategoryScholarship.copy(alpha = 0.15f), CategoryScholarship)
        "holiday", "leave" -> Pair(CategoryHoliday.copy(alpha = 0.15f), CategoryHoliday)
        "events", "event" -> Pair(CategoryEvents.copy(alpha = 0.15f), CategoryEvents)
        "hostel" -> Pair(CategoryHostel.copy(alpha = 0.15f), CategoryHostel)
        "placement" -> Pair(CategoryPlacement.copy(alpha = 0.15f), CategoryPlacement)
        else -> Pair(CategoryGeneral.copy(alpha = 0.15f), CategoryGeneral)
    }

    val displayText = buildString {
        append(category)
        if (confidence != null && confidence > 0.0) {
            append(" (${(confidence * 100).toInt()}%)")
        }
    }

    Box(
        modifier = modifier
            .background(badgeBg, shape = RoundedCornerShape(16.dp))
            .padding(horizontal = 12.dp, vertical = 6.dp)
    ) {
        Text(
            text = displayText,
            color = textColor,
            fontSize = 12.sp,
            fontWeight = FontWeight.Bold
        )
    }
}
