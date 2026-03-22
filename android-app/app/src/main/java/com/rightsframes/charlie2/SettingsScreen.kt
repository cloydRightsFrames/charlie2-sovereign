package com.rightsframes.charlie2

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(onBack: () -> Unit) {
    var baseUrl    by remember { mutableStateOf(Charlie2Client.baseUrl) }
    var ollamaUrl  by remember { mutableStateOf(Charlie2Client.ollamaUrl) }
    var railwayUrl by remember { mutableStateOf(Charlie2Client.railwayUrl) }
    var saved      by remember { mutableStateOf(false) }

    Box(Modifier.fillMaxSize().background(C2Colors.BgDark)) {
        Column(Modifier.fillMaxSize()) {
            Box(Modifier.fillMaxWidth().background(C2Colors.BgCard)
                .padding(horizontal = 8.dp, vertical = 4.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, "Back", tint = C2Colors.Cyan)
                    }
                    Text("Settings", color = C2Colors.Cyan,
                        fontWeight = FontWeight.Bold, fontSize = 16.sp,
                        fontFamily = FontFamily.Monospace)
                }
            }
            Column(
                Modifier.fillMaxSize()
                    .verticalScroll(rememberScrollState())
                    .padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(14.dp)
            ) {
                SettingsSection("Phone Node") {
                    SettingsField("Governance API URL", baseUrl) { baseUrl = it }
                }
                SettingsSection("Ollama Local AI") {
                    SettingsField("Ollama URL", ollamaUrl) { ollamaUrl = it }
                }
                SettingsSection("Railway Cloud") {
                    SettingsField("Railway URL (optional)", railwayUrl) { railwayUrl = it }
                    Text("Leave empty to use local Ollama only",
                        color = C2Colors.Muted, fontSize = 11.sp,
                        fontFamily = FontFamily.Monospace)
                }
                SettingsSection("WireGuard Mesh") {
                    Text("Phone: 10.99.0.1", color = C2Colors.Green,
                        fontSize = 12.sp, fontFamily = FontFamily.Monospace)
                    Text("PC:    10.99.0.2", color = C2Colors.Yellow,
                        fontSize = 12.sp, fontFamily = FontFamily.Monospace)
                }
                SettingsSection("Tor Hidden Service") {
                    Text("2feulm4uczwznjvapwadeardwmzpco6jhyarp4t2abguthyhczwyfxid.onion",
                        color = C2Colors.Purple, fontSize = 10.sp,
                        fontFamily = FontFamily.Monospace)
                }
                Button(
                    onClick = {
                        Charlie2Client.baseUrl    = baseUrl.trimEnd('/')
                        Charlie2Client.ollamaUrl  = ollamaUrl.trimEnd('/')
                        Charlie2Client.railwayUrl = railwayUrl.trimEnd('/')
                        saved = true
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = C2Colors.Cyan),
                    shape = RoundedCornerShape(10.dp),
                    modifier = Modifier.fillMaxWidth().height(48.dp)
                ) {
                    Text("SAVE", color = Color.Black,
                        fontWeight = FontWeight.Bold, fontSize = 14.sp)
                }
                if (saved) {
                    Text("Saved", color = C2Colors.Green,
                        fontSize = 13.sp, fontFamily = FontFamily.Monospace,
                        modifier = Modifier.align(Alignment.CenterHorizontally))
                }
            }
        }
    }
}

@Composable
fun SettingsSection(title: String, content: @Composable ColumnScope.() -> Unit) {
    Column(
        Modifier.fillMaxWidth()
            .background(C2Colors.BgCard, RoundedCornerShape(10.dp))
            .padding(14.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        Text(title, color = C2Colors.Muted, fontSize = 11.sp,
            fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace,
            modifier = Modifier.padding(bottom = 4.dp))
        content()
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsField(label: String, value: String, onValueChange: (String) -> Unit) {
    OutlinedTextField(
        value = value, onValueChange = onValueChange,
        label = { Text(label, color = C2Colors.Muted, fontSize = 11.sp) },
        modifier = Modifier.fillMaxWidth(),
        colors = OutlinedTextFieldDefaults.colors(
            focusedBorderColor      = C2Colors.Cyan,
            unfocusedBorderColor    = C2Colors.Border,
            focusedTextColor        = C2Colors.TextLight,
            unfocusedTextColor      = C2Colors.TextLight,
            cursorColor             = C2Colors.Cyan,
            focusedContainerColor   = C2Colors.BgItem,
            unfocusedContainerColor = C2Colors.BgItem,
            focusedLabelColor       = C2Colors.Cyan),
        shape = RoundedCornerShape(8.dp), singleLine = true,
        textStyle = LocalTextStyle.current.copy(
            fontSize = 12.sp, fontFamily = FontFamily.Monospace))
}
