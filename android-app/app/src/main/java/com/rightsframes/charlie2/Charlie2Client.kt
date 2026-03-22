package com.rightsframes.charlie2

import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

object Charlie2Client {
    var baseUrl    = "http://10.99.0.1:8000"
    var ollamaUrl  = "http://10.99.0.1:11434"
    var railwayUrl = ""

    private fun get(url: String, timeoutMs: Int = 8000): String {
        return try {
            val c = URL(url).openConnection() as HttpURLConnection
            c.connectTimeout = timeoutMs; c.readTimeout = timeoutMs
            c.inputStream.bufferedReader().readText()
        } catch (e: Exception) { "{\"error\":\"${e.message}\"}" }
    }

    private fun post(url: String, body: String, timeoutMs: Int = 30000): String {
        return try {
            val c = URL(url).openConnection() as HttpURLConnection
            c.requestMethod = "POST"; c.doOutput = true
            c.connectTimeout = 8000; c.readTimeout = timeoutMs
            c.setRequestProperty("Content-Type", "application/json")
            c.outputStream.write(body.toByteArray())
            c.inputStream.bufferedReader().readText()
        } catch (e: Exception) { "{\"error\":\"${e.message}\"}" }
    }

    fun health(): Pair<String, String> {
        return try {
            val j = JSONObject(get("$baseUrl/health"))
            Pair(j.optString("status","OFFLINE"), j.optString("memory","--"))
        } catch (e: Exception) { Pair("OFFLINE","--") }
    }

    fun auditCount(): Int {
        return try {
            JSONObject(get("$baseUrl/audit")).optJSONArray("judicial")?.length() ?: 0
        } catch (e: Exception) { 0 }
    }

    fun getAudit(): String = get("$baseUrl/audit", 10000)

    fun clusterStatus(): String = get("http://10.99.0.1:8002/cluster-status", 5000)

    fun chat(prompt: String): Pair<String, String> {
        val escaped = prompt.replace("\"","\\\"").replace("\n","\\n")
        val body = """{"model":"deepseek-coder:1.3b","prompt":"$escaped","stream":false}"""
        return try {
            val j = JSONObject(post("$ollamaUrl/api/generate", body))
            val r = j.optString("response","")
            if (r.isNotEmpty()) Pair(r,"ollama:local") else tryCloud(prompt)
        } catch (e: Exception) { tryCloud(prompt) }
    }

    private fun tryCloud(prompt: String): Pair<String, String> {
        if (railwayUrl.isEmpty()) return Pair(
            "Local AI offline. Run: bash ~/charlie2/ollama_start.sh","offline")
        return try {
            val escaped = prompt.replace("\"","\\\"")
            val j = JSONObject(post("$railwayUrl/infer","""{"prompt":"$escaped"}"""))
            Pair(j.optString("response","No response"),"railway:cloud")
        } catch (e: Exception) { Pair("All nodes offline.","offline") }
    }
}
