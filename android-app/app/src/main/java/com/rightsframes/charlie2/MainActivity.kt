package com.rightsframes.charlie2

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Send
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.*
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

// ⚡ Charlie 2.0 — Sovereign Android App
// RightsFrames Intelligence / cloydRightsFrames

object C2Colors {
    val BgDark    = Color(0xFF0D1117)
    val BgCard    = Color(0xFF161B22)
    val BgItem    = Color(0xFF21262D)
    val Cyan      = Color(0xFF00D4FF)
    val Green     = Color(0xFF3FB950)
    val Yellow    = Color(0xFFE3B341)
    val Red       = Color(0xFFF85149)
    val TextLight = Color(0xFFE6EDF3)
    val Muted     = Color(0xFF8B949E)
    val Border    = Color(0xFF30363D)
}

data class ChatMessage(
    val role: String,
    val content: String,
    val provider: String = "ollama",
    val ts: Long = System.currentTimeMillis()
)

object Charlie2Client {
    var baseUrl     = "http://10.99.0.1:8000"    // WireGuard mesh — phone
    var ollamaUrl   = "http://10.99.0.1:11434"   // Ollama on phone
    var railwayUrl  = ""                          // Set after Railway deploy

    private fun post(url: String, body: String, timeoutMs: Int = 30000): String {
        return try {
            val c = URL(url).openConnection() as HttpURLConnection
            c.requestMethod = "POST"
            c.doOutput = true
            c.connectTimeout = 8000
            c.readTimeout = timeoutMs
            c.setRequestProperty("Content-Type", "application/json")
            c.outputStream.write(body.toByteArray())
            c.inputStream.bufferedReader().readText()
        } catch (e: Exception) { "{\"error\":\"${e.message}\"}" }
    }

    private fun get(url: String): String {
        return try {
            val c = URL(url).openConnection() as HttpURLConnection
            c.connectTimeout = 5000; c.readTimeout = 10000
            c.inputStream.bufferedReader().readText()
        } catch (e: Exception) { "{\"error\":\"${e.message}\"}" }
    }

    fun health(): Pair<String, String> {
        val raw = get("$baseUrl/health")
        return try {
            val j = JSONObject(raw)
            Pair(j.optString("status", "OFFLINE"), j.optString("memory", "--"))
        } catch (e: Exception) { Pair("OFFLINE", "--") }
    }

    fun auditCount(): Int {
        val raw = get("$baseUrl/audit")
        return try {
            JSONObject(raw).optJSONArray("judicial")?.length() ?: 0
        } catch (e: Exception) { 0 }
    }

    fun chat(prompt: String): Pair<String, String> {
        // 1. Try local Ollama first
        val body = """{"model":"deepseek-coder:1.3b","prompt":"$prompt","stream":false}"""
        val resp = post("$ollamaUrl/api/generate", body)
        return try {
            val j = JSONObject(resp)
            val r = j.optString("response", "")
            if (r.isNotEmpty()) Pair(r, "ollama:local")
            else tryRailway(prompt)
        } catch (e: Exception) { tryRailway(prompt) }
    }

    private fun tryRailway(prompt: String): Pair<String, String> {
        if (railwayUrl.isEmpty()) return Pair(
            "Ollama offline. Set railwayUrl or run: bash ~/charlie2/ollama_start.sh",
            "offline"
        )
        val body = """{"prompt":"$prompt"}"""
        val resp = post("$railwayUrl/infer", body)
        return try {
            Pair(JSONObject(resp).optString("result", "No response"), "railway:cloud")
        } catch (e: Exception) {
            Pair("All providers offline.", "offline")
        }
    }
}

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { MaterialTheme { Charlie2Screen() } }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun Charlie2Screen() {
    val messages  = remember { mutableStateListOf<ChatMessage>() }
    var input     by remember { mutableStateOf("") }
    var status    by remember { mutableStateOf("connecting...") }
    var memUsed   by remember { mutableStateOf("--") }
    var audits    by remember { mutableStateOf(0) }
    var provider  by remember { mutableStateOf("ollama") }
    var loading   by remember { mutableStateOf(false) }
    val scope     = rememberCoroutineScope()
    val listState = rememberLazyListState()

    LaunchedEffect(Unit) {
        withContext(Dispatchers.IO) {
            val (s, m) = Charlie2Client.health()
            val a = Charlie2Client.auditCount()
            status = s; memUsed = m; audits = a
        }
    }

    LaunchedEffect(messages.size) {
        if (messages.isNotEmpty()) listState.animateScrollToItem(messages.size - 1)
    }

    Box(Modifier.fillMaxSize().background(C2Colors.BgDark)) {
        Column(Modifier.fillMaxSize()) {

            // Header
            Box(
                Modifier.fillMaxWidth()
                    .background(C2Colors.BgCard)
                    .padding(horizontal = 16.dp, vertical = 12.dp)
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        Modifier.size(9.dp).clip(RoundedCornerShape(50))
                            .background(if (status == "OK") C2Colors.Green else C2Colors.Red)
                    )
                    Spacer(Modifier.width(10.dp))
                    Column {
                        Text("⚡ CHARLIE 2.0",
                            color = C2Colors.Cyan, fontWeight = FontWeight.Bold,
                            fontSize = 15.sp, fontFamily = FontFamily.Monospace)
                        Text("$status · $memUsed · $audits audits · $provider",
                            color = C2Colors.Muted, fontSize = 10.sp,
                            fontFamily = FontFamily.Monospace)
                    }
                }
            }

            // Messages
            LazyColumn(
                state = listState,
                modifier = Modifier.weight(1f).padding(12.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                if (messages.isEmpty()) {
                    item {
                        Box(Modifier.fillMaxWidth().padding(top = 60.dp),
                            contentAlignment = Alignment.Center) {
                            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                Text("⚡", fontSize = 52.sp)
                                Spacer(Modifier.height(10.dp))
                                Text("Charlie 2.0",
                                    color = C2Colors.Cyan, fontSize = 22.sp,
                                    fontWeight = FontWeight.Bold)
                                Spacer(Modifier.height(4.dp))
                                Text("Sovereign AI · RightsFrames Intelligence",
                                    color = C2Colors.Muted, fontSize = 12.sp)
                                Spacer(Modifier.height(4.dp))
                                Text("Tri-Branch Governance · Local AI · Tor",
                                    color = C2Colors.Muted, fontSize = 10.sp,
                                    fontFamily = FontFamily.Monospace)
                            }
                        }
                    }
                }
                items(messages) { msg -> MessageBubble(msg) }
                if (loading) {
                    item {
                        Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
                            Row(verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                CircularProgressIndicator(
                                    color = C2Colors.Cyan,
                                    modifier = Modifier.size(16.dp),
                                    strokeWidth = 2.dp)
                                Text("Charlie 2.0 thinking...",
                                    color = C2Colors.Muted, fontSize = 11.sp,
                                    fontFamily = FontFamily.Monospace)
                            }
                        }
                    }
                }
            }

            // Input
            Row(
                Modifier.fillMaxWidth()
                    .background(C2Colors.BgCard)
                    .padding(10.dp),
                verticalAlignment = Alignment.Bottom
            ) {
                OutlinedTextField(
                    value = input,
                    onValueChange = { input = it },
                    modifier = Modifier.weight(1f),
                    placeholder = {
                        Text("Ask Charlie 2.0...", color = C2Colors.Muted, fontSize = 13.sp)
                    },
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor   = C2Colors.Cyan,
                        unfocusedBorderColor = C2Colors.Border,
                        focusedTextColor     = C2Colors.TextLight,
                        unfocusedTextColor   = C2Colors.TextLight,
                        cursorColor          = C2Colors.Cyan,
                        focusedContainerColor   = C2Colors.BgItem,
                        unfocusedContainerColor = C2Colors.BgItem
                    ),
                    shape = RoundedCornerShape(10.dp),
                    maxLines = 4,
                    textStyle = LocalTextStyle.current.copy(fontSize = 14.sp)
                )
                Spacer(Modifier.width(8.dp))
                Button(
                    onClick = {
                        if (input.isBlank() || loading) return@Button
                        val q = input.trim(); input = ""; loading = true
                        messages.add(ChatMessage("user", q))
                        scope.launch {
                            val (resp, prov) = withContext(Dispatchers.IO) {
                                Charlie2Client.chat(q)
                            }
                            provider = prov
                            messages.add(ChatMessage("charlie", resp, prov))
                            loading = false
                            audits = withContext(Dispatchers.IO) { Charlie2Client.auditCount() }
                        }
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = C2Colors.Cyan),
                    shape = RoundedCornerShape(10.dp),
                    modifier = Modifier.size(56.dp),
                    contentPadding = PaddingValues(0.dp)
                ) {
                    Icon(Icons.Default.Send, contentDescription = "Send",
                        tint = Color.Black, modifier = Modifier.size(20.dp))
                }
            }
        }
    }
}

@Composable
fun MessageBubble(msg: ChatMessage) {
    val isUser = msg.role == "user"
    Row(
        Modifier.fillMaxWidth(),
        horizontalArrangement = if (isUser) Arrangement.End else Arrangement.Start
    ) {
        Column(
            horizontalAlignment = if (isUser) Alignment.End else Alignment.Start,
            modifier = Modifier.widthIn(max = 290.dp)
        ) {
            if (!isUser) {
                Text("⚡ ${msg.provider}",
                    color = C2Colors.Green, fontSize = 9.sp,
                    fontFamily = FontFamily.Monospace,
                    modifier = Modifier.padding(start = 4.dp, bottom = 3.dp))
            }
            Box(
                Modifier
                    .clip(RoundedCornerShape(
                        topStart    = if (isUser) 12.dp else 2.dp,
                        topEnd      = if (isUser) 2.dp else 12.dp,
                        bottomStart = 12.dp,
                        bottomEnd   = 12.dp))
                    .background(
                        if (isUser)
                            Brush.linearGradient(listOf(Color(0xFF1A3A4A), Color(0xFF0D2233)))
                        else
                            Brush.linearGradient(listOf(C2Colors.BgCard, C2Colors.BgItem)))
                    .padding(10.dp, 8.dp)
            ) {
                Text(msg.content, color = C2Colors.TextLight,
                    fontSize = 13.sp, lineHeight = 19.sp)
            }
        }
    }
}
