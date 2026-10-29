
const themeToggle = document.getElementById("theme-toggle");
const themeIcon = document.getElementById("theme-icon");
const themeLabel = document.getElementById("theme-label");

function applyTheme(theme) {
    document.body.dataset.theme = theme;

    const isDark = theme === "dark";

    themeIcon.textContent = isDark ? "☀️" : "🌙";
    themeLabel.textContent = isDark ? "Light mode" : "Dark mode";

    themeToggle.setAttribute(
        "aria-label",
        isDark ? "Switch to light mode" : "Switch to dark mode"
    );
}

// Use the theme loaded by Flask from PostgreSQL
const savedTheme = document.body.dataset.theme;
applyTheme(savedTheme === "dark" ? "dark" : "light");

themeToggle.addEventListener("click", async () => {
    const currentTheme = document.body.dataset.theme;
    const newTheme = currentTheme === "dark" ? "light" : "dark";

    // Change the appearance immediately
    applyTheme(newTheme);
    themeToggle.disabled = true;

    try {
        const response = await fetch("/api/theme", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ theme: newTheme })
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || "Could not save theme.");
        }
    } catch (error) {
        // Revert if saving failed, so the page matches the saved preference
        applyTheme(currentTheme);
        alert("Your theme could not be saved. Please try again.");
        console.error("Theme update failed:", error);
    } finally {
        themeToggle.disabled = false;
    }
});
