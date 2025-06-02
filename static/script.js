function spocitatCestu() {
    const origin = document.getElementById("origin").value;
    const destination = document.getElementById("destination").value;

    fetch("/vypocet", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ origin: origin, destination: destination })
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById("vystup").textContent = data.vystup;
    })
    .catch(err => {
        document.getElementById("vystup").textContent = "Chyba při volání serveru: " + err;
    });
}
