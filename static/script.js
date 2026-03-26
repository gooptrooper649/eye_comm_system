function sendText(text) {
    fetch('/speak', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: text })
    });
}

let lastBlink = 0;

if (data.blink && Date.now() - lastBlink > 1500) {
    const text = buttons[selectedIndex].innerText;
    speak(text);
    lastBlink = Date.now();
}
let selectedIndex = 0;
const buttons = document.querySelectorAll("button");

function highlight() {
    buttons.forEach(btn => btn.classList.remove("selected"));
    buttons[selectedIndex].classList.add("selected");
}

function speak(text) {
    fetch('/speak', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: text })
    });
}

async function trackEyes() {
    const res = await fetch('/eye_data');
    const data = await res.json();

    if (data.gaze === "LEFT") {
        selectedIndex = Math.max(0, selectedIndex - 1);
    } else if (data.gaze === "RIGHT") {
        selectedIndex = Math.min(buttons.length - 1, selectedIndex + 1);
    }

    if (data.blink) {
        const text = buttons[selectedIndex].innerText;
        speak(text);
    }

    highlight();
}

setInterval(trackEyes, 500);
highlight();