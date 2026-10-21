
package com.agentsimulation.engine

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

/**
 * Local persistent task history for the Android application.
 *
 * Records remain in this app's private storage. This class does not
 * execute tasks or synchronise them with the Python engine.
 */
class AgentTaskStore(context: Context) {

    private val preferences = context.getSharedPreferences(
        PREFERENCES_NAME,
        Context.MODE_PRIVATE
    )

    @Synchronized
    fun loadTasks(): List<AgentTask> {
        return try {
            val json = preferences.getString(KEY_TASKS, "[]") ?: "[]"
            val array = JSONArray(json)
            val tasks = mutableListOf<AgentTask>()

            for (index in 0 until array.length()) {
                val item = array.optJSONObject(index) ?: continue
                val status = item.optString(
                    "status",
                    AgentTask.STATUS_QUEUED
                )

                tasks.add(
                    AgentTask(
                        id = item.optString("id", ""),
                        title = item.optString("title", ""),
                        instructions = item.optString("instructions", ""),
                        assignedAgentId = item.optString(
                            "assignedAgentId",
                            "boss"
                        ),
                        status = if (status in AgentTask.ALL_STATUSES) {
                            status
                        } else {
                            AgentTask.STATUS_QUEUED
                        },
                        result = item.optString("result", ""),
                        createdAt = item.optLong("createdAt", 0L),
                        updatedAt = item.optLong("updatedAt", 0L)
                    )
                )
            }

            tasks.sortedByDescending { it.createdAt }
        } catch (_: Exception) {
            emptyList()
        }
    }

    @Synchronized
    fun findTask(taskId: String): AgentTask? {
        return loadTasks().firstOrNull { it.id == taskId }
    }

    @Synchronized
    fun saveTask(task: AgentTask): Boolean {
        val tasks = loadTasks().toMutableList()
        val index = tasks.indexOfFirst { it.id == task.id }

        if (index >= 0) {
            tasks[index] = task
        } else {
            tasks.add(task)
        }

        val array = JSONArray()

        tasks.takeLast(MAX_TASKS).forEach { item ->
            array.put(
                JSONObject()
                    .put("id", item.id)
                    .put("title", item.title)
                    .put("instructions", item.instructions)
                    .put("assignedAgentId", item.assignedAgentId)
                    .put("status", item.status)
                    .put("result", item.result)
                    .put("createdAt", item.createdAt)
                    .put("updatedAt", item.updatedAt)
            )
        }

        return preferences.edit()
            .putString(KEY_TASKS, array.toString())
            .commit()
    }

    @Synchronized
    fun deleteTask(taskId: String): Boolean {
        val remaining = loadTasks().filterNot { it.id == taskId }
        val array = JSONArray()

        remaining.forEach { item ->
            array.put(
                JSONObject()
                    .put("id", item.id)
                    .put("title", item.title)
                    .put("instructions", item.instructions)
                    .put("assignedAgentId", item.assignedAgentId)
                    .put("status", item.status)
                    .put("result", item.result)
                    .put("createdAt", item.createdAt)
                    .put("updatedAt", item.updatedAt)
            )
        }

        return preferences.edit()
            .putString(KEY_TASKS, array.toString())
            .commit()
    }

    companion object {
        private const val PREFERENCES_NAME = "agent_simulation_task_store"
        private const val KEY_TASKS = "agent_tasks"
        private const val MAX_TASKS = 500
    }
}
