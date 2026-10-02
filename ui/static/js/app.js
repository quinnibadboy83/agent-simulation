document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".tab").forEach(tab => {
        tab.addEventListener("click", () => {
            document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
            document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
            
            tab.classList.add("active");
            document.getElementById(tab.dataset.tab).classList.add("active");
        });
    });

    const form = document.getElementById("command-form");
    const input = document.getElementById("command-input");
    const responseArea = document.getElementById("response-area");

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const command = input.value.trim();
        if (!command) return;

        responseArea.textContent = "Processing...";
        input.value = "";
        input.blur();

        try {
            const formData = new FormData();
            formData.append("command", command);

            const res = await fetch("/command", {
                method: "POST",
                body: formData
            });
            const data = await res.json();

            responseArea.textContent = data.response;

            if (data.balance !== undefined) {
                document.getElementById("balance").textContent = data.balance.toFixed(2);
            }
            if (data.knowledge_count !== undefined) {
                const el = document.getElementById("knowledge-count");
                if (el) el.textContent = data.knowledge_count;
            }
        } catch (err) {
            responseArea.textContent = "Error contacting system: " + err.message;
        }
    });

    document.getElementById("advance-time").addEventListener("click", async () => {
        try {
            const res = await fetch("/api/advance_time", { method: "POST" });
            const data = await res.json();
            document.getElementById("day").textContent = data.world.day;
            document.getElementById("time").textContent = data.world.time;
            responseArea.textContent = `Time advanced → Day ${data.world.day} - ${data.world.time}`;
        } catch (err) {
            console.error(err);
        }
    });
});

function sendQuick(cmd) {
    const input = document.getElementById("command-input");
    input.value = cmd;
    document.getElementById("command-form").dispatchEvent(new Event("submit"));
}
