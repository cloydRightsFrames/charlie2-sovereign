package com.rightsframes.charlie2

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.*
import org.json.JSONArray
import org.json.JSONObject

data class AuditEntry(
    val branch: String, val event: String,
    val verdict: String, val hash: String, val ts: Double
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AuditScreen(onBack: () -> Unit) {
    var judicial    by remember { mutableStateOf(listOf<AuditEntry>()) }
    var legislative by remember { mutableStateOf(listOf<AuditEntry>()) }
    var executive   by remember { mutableStateOf(listOf<AuditEntry>()) }
    var loading     by remember { mutableStateOf(true) }
    var activeTab   by remember { mutableStateOf(0) }
    val scope = rememberCoroutineScope()

    fun load() {
        loading = true
        scope.launch {
            val raw = withContext(Dispatchers.IO) { Charlie2Client.getAudit() }
            try {
                val j = JSONObject(raw)
                judicial    = parseEntries(j.optJSONArray("judicial"),    "judicial")
                legislative = parseEntries(j.optJSONArray("legislative"), "legislative")
                executive   = parseEntries(j.optJSONArray("executive"),   "executive")
            } catch (e: Exception) {}
            loading = false
        }
    }

    LaunchedEffect(Unit) { load() }

    Box(Modifier.fillMaxSize().background(C2Colors.BgDark)) {
        Column(Modifier.fillMaxSize()) {
            Box(Modifier.fillMaxWidth().background(C2Colors.BgCard)
                .padding(horizontal = 8.dp, vertical = 4.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, "Back", tint = C2Colors.Cyan)
                    }
                    Text("Governance Chain", color = C2Colors.Cyan,
                        fontWeight = FontWeight.Bold, fontSize = 15.sp,
                        fontFamily = FontFamily.Monospace)
                    Spacer(Modifier.weight(1f))
                    IconButton(onClick = { load() }) {
                        Icon(Icons.Default.Refresh, "Refresh", tint = C2Colors.Muted)
                    }
                }
            }
            Row(Modifier.fillMaxWidth().background(C2Colors.BgCard)
                .padding(horizontal = 12.dp)) {
                listOf("JUDICIAL" to judicial.size,
                       "LEGISLATIVE" to legislative.size,
                       "EXECUTIVE" to executive.size
                ).forEachIndexed { i, (label, count) ->
                    val col = when(i) { 0->C2Colors.Red; 1->C2Colors.Yellow; else->C2Colors.Cyan }
                    TextButton(onClick = { activeTab = i }) {
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            Text(count.toString(),
                                color = if (activeTab==i) col else C2Colors.Muted,
                                fontSize = 16.sp, fontWeight = FontWeight.Bold,
                                fontFamily = FontFamily.Monospace)
                            Text(label,
                                color = if (activeTab==i) col else C2Colors.Muted,
                                fontSize = 9.sp, fontFamily = FontFamily.Monospace)
                        }
                    }
                    if (i < 2) Spacer(Modifier.weight(1f))
                }
            }
            if (loading) {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator(color = C2Colors.Cyan)
                }
            } else {
                val entries = when(activeTab) {
                    0 -> judicial; 1 -> legislative; else -> executive }
                LazyColumn(Modifier.fillMaxSize().padding(12.dp),
                    verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    items(entries) { AuditCard(it) }
                    if (entries.isEmpty()) {
                        item {
                            Box(Modifier.fillMaxWidth().padding(top=40.dp),
                                contentAlignment = Alignment.Center) {
                                Text("No records yet", color = C2Colors.Muted,
                                    fontFamily = FontFamily.Monospace)
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun AuditCard(entry: AuditEntry) {
    val verdictColor = if (entry.verdict=="APPROVED") C2Colors.Green else C2Colors.Red
    val branchColor  = when(entry.branch) {
        "judicial"->;C2Colors.Red; "legislative"->C2Colors.Yellow; else->C2Colors.Cyan }
    Row(Modifier.fillMaxWidth()
        .background(C2Colors.BgCard, RoundedCornerShape(8.dp))
        .padding(10.dp,8.dp),
        verticalAlignment = Alignment.CenterVertically) {
        Column(Modifier.weight(1f)) {
            Row(verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                Text(entry.branch.uppercase(), color = branchColor,
                    fontSize = 9.sp, fontWeight = FontWeight.Bold,
                    fontFamily = FontFamily.Monospace)
                Text(entry.verdict, color = verdictColor,
                    fontSize = 9.sp, fontFamily = FontFamily.Monospace)
            }
            Text(entry.event.take(55), color = C2Colors.TextLight,
                fontSize = 12.sp, fontFamily = FontFamily.Monospace,
                modifier = Modifier.padding(top=3.dp))
            Text("[${entry.hash.take(12)}]", color = C2Colors.Purple,
                fontSize = 10.sp, fontFamily = FontFamily.Monospace,
                modifier = Modifier.padding(top=2.dp))
        }
    }
}

fun parseEntries(arr: JSONArray?, branch: String): List<AuditEntry> {
    if (arr == null) return emptyList()
    val list = mutableListOf<AuditEntry>()
    for (i in 0 until arr.length()) {
        val o = arr.optJSONObject(i) ?: continue
        list.add(AuditEntry(
            branch  = branch,
            event   = o.optString("event",
                      o.optString("policy",
                      o.optString("action","--"))),
            verdict = o.optString("verdict", o.optString("status","OK")),
            hash    = o.optString("hash",""),
            ts      = o.optDouble("ts",0.0)))
    }
    return list
}
