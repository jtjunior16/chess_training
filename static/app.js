// Board page: load a position, let the player move, then show the engine's top moves.
import { Chessground } from "https://cdn.jsdelivr.net/npm/chessground@9.2.1/dist/chessground.js";

const $ = (id) => document.getElementById(id);
const BRUSHES = ["green", "blue", "yellow"]; // arrows for engine moves #1, #2, #3

let cg = null;
let position = null;

function formatScore(score) {
  // Scores are from the player's point of view (the side to move).
  if (score.mate !== null) return score.mate > 0 ? `mate in ${score.mate}` : `mated in ${-score.mate}`;
  const pawns = score.cp / 100;
  return (pawns > 0 ? "+" : "") + pawns.toFixed(2);
}

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

async function loadPosition() {
  const res = await fetch("/api/position");
  position = await res.json();

  $("result").hidden = true;
  $("result").innerHTML = "";
  $("only-move").checked = false;
  $("only-move").disabled = false;

  const label = [position.phase, position.opening].filter(Boolean).join(" · ");
  $("meta").textContent = label;
  $("prompt").textContent = `${position.turn === "white" ? "White" : "Black"} to move. ${position.description}`;

  const config = {
    fen: position.fen,
    orientation: position.turn,
    turnColor: position.turn,
    lastMove: undefined,
    movable: {
      free: false,
      color: position.turn,
      dests: new Map(Object.entries(position.dests)),
      showDests: true,
      events: { after: onMove },
    },
    drawable: { autoShapes: [] },
  };
  if (cg) cg.set(config);
  else cg = Chessground($("board"), config);
}

async function onMove(orig, dest) {
  cg.set({ movable: { color: undefined, dests: new Map() } }); // lock the board
  $("only-move").disabled = true;
  $("result").hidden = false;
  $("result").textContent = "Thinking…";

  const res = await fetch("/api/move", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ fen: position.fen, move: orig + dest, only_move: $("only-move").checked }),
  });
  const data = await res.json();
  if (!res.ok) {
    $("result").textContent = `Error: ${data.detail}`;
    return;
  }
  showResult(data, orig, dest);
}

function showResult(data, orig, dest) {
  const shapes = data.top.map((line, i) => ({
    orig: line.uci.slice(0, 2),
    dest: line.uci.slice(2, 4),
    brush: BRUSHES[i],
  }));
  if (!data.in_top) shapes.push({ orig, dest, brush: "red" });
  cg.setAutoShapes(shapes);

  const verdict = data.in_top
    ? `Your move <b>${escapeHtml(data.player.san)}</b> is engine move #${data.rank}.`
    : `Your move <b>${escapeHtml(data.player.san)}</b> is not in the top ${data.top.length}.`;
  const rows = data.top
    .map(
      (line, i) =>
        `<li class="${BRUSHES[i]}"><b>${escapeHtml(line.san)}</b> ${formatScore(line.score)}` +
        ` <span class="pv">${escapeHtml(line.pv.join(" "))}</span></li>`,
    )
    .join("");
  const gap = data.gap_cp === null ? "n/a" : (data.gap_cp / 100).toFixed(2);
  const claim = data.only_move_claim ? "You said: only good move." : "You said: not an only-move position.";

  $("result").innerHTML = `
    <p>${verdict}</p>
    <p>Your move: ${formatScore(data.player.score)} · lost <b>${(data.loss_cp / 100).toFixed(2)}</b> pawns vs the best move.</p>
    <ol class="top">${rows}</ol>
    <p class="small">${claim} Gap between best and 2nd best: ${gap} pawns.</p>`;
}

$("next").addEventListener("click", loadPosition);
loadPosition();
