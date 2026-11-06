// Interactive seat selection: limits seat count and updates the running total.
(function () {
  const cfg = window.SEAT_CONFIG || { price: 0, max: 10 };
  const boxes = document.querySelectorAll('.seat input[type="checkbox"]:not(:disabled)');
  const selectedEl = document.getElementById("selected-seats");
  const totalEl = document.getElementById("total");
  const proceed = document.getElementById("proceed");

  function update() {
    const chosen = Array.from(boxes).filter((b) => b.checked).map((b) => b.value);
    selectedEl.textContent = chosen.length ? chosen.join(", ") : "none";
    totalEl.textContent = (chosen.length * cfg.price).toLocaleString("en-IN");
    proceed.disabled = chosen.length === 0;
    proceed.textContent = chosen.length
      ? `Proceed to pay (${chosen.length} seat${chosen.length > 1 ? "s" : ""})`
      : "Proceed to pay";
  }

  boxes.forEach((box) => {
    box.addEventListener("change", () => {
      const count = Array.from(boxes).filter((b) => b.checked).length;
      if (box.checked && count > cfg.max) {
        box.checked = false;
        alert(`You can select up to ${cfg.max} seats per booking.`);
      }
      box.closest(".seat").classList.toggle("selected", box.checked);
      update();
    });
  });
  update();
})();
