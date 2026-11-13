from drafter import *
from dataclasses import dataclass
import random
import time

set_website_title("Lacrosse Shootout")

ROUNDS = 10
SIZE = 5
HARD_TIME_LIMIT = 3.0


@dataclass
class State:
    name: str
    difficulty: str
    mode: str
    shots_taken: int
    goals: int
    saves: int
    misses: int
    shot_counts: list[int]
    last_shot: int
    last_ar: int
    last_ac: int
    shot_start: float
    message: str

def goalie_body(ar: int, ac: int) -> dict[int, str]:
    """Body cells {cell_index: emoji}: head, arms, torso, split legs."""
    shape = [
        (ar - 1, ac, "🙂"),
        (ar, ac - 1, "🟦"),
        (ar, ac, "🟦"),
        (ar, ac + 1, "🟦"),
        (ar + 1, ac - 1, "🟦"),
        (ar + 1, ac + 1, "🟦"),
    ]
    return {r * SIZE + c: emoji for r, c, emoji in shape}


def goalie_stick(ar: int, ac: int) -> dict[int, str]:
    """Stick cells held out to the side the goalie has room on."""
    side = 2 if ac <= 2 else -2
    col = ac + side
    return {
        (ar - 1) * SIZE + col: "🟫",
        ar * SIZE + col: "🟫",
    }


def goalie_choose_anchor(state: State) -> tuple[int, int]:
    """Goalie predicts your shot from your habits, then moves to cover it."""
    if state.difficulty == "Easy":
        weights = [1] * (SIZE * SIZE)
    elif state.difficulty == "Medium":
        weights = [1 + count for count in state.shot_counts]
    else:
        weights = [1 + count * 3 for count in state.shot_counts]
        if state.last_shot != -1:
            weights[state.last_shot] += 3

    predicted = random.choices(range(SIZE * SIZE), weights=weights)[0]
    row, col = divmod(predicted, SIZE)
    ar = min(max(row, 1), SIZE - 2)
    ac = min(max(col, 1), SIZE - 2)
    return ar, ac


def near_body(spot: int, body: dict[int, str]) -> bool:
    sr, sc = divmod(spot, SIZE)
    for cell in body:
        br, bc = divmod(cell, SIZE)
        if abs(sr - br) <= 1 and abs(sc - bc) <= 1:
            return True
    return False


def resolve_shot(state: State, spot: int, body: dict[int, str], stick: dict[int, str]) -> str:
    """Return 'miss', 'save', 'stick', or 'goal'."""
    row, col = divmod(spot, SIZE)
    on_edge = row in (0, SIZE - 1) or col in (0, SIZE - 1)

    if state.mode == "Power" and on_edge and random.random() < 0.20:
        return "miss"

    if spot in body:
        if state.mode == "Power" and random.random() < 0.25:
            return "goal"
        return "save"

    if spot in stick:
        stick_chance = 0.85 if state.difficulty == "Hard" else 0.70
        if state.mode == "Power":
            stick_chance -= 0.20   
        if random.random() < stick_chance:
            return "stick"
        return "goal"
    
    if state.mode == "Accurate" and near_body(spot, body) and random.random() < 0.25:
        return "save"

    return "goal"



def build_goal_table(shot: int, ar: int, ac: int) -> Table:
    """Static picture of the net after a shot."""
    body = goalie_body(ar, ac)
    stick = goalie_stick(ar, ac)
    rows = []
    for r in range(SIZE):
        row = []
        for c in range(SIZE):
            i = r * SIZE + c
            if i == shot:
                row.append("🟠")
            elif i in body:
                row.append(body[i])
            elif i in stick:
                row.append(stick[i])
            else:
                row.append("⬜")
        rows.append(row)
    return Table(rows)


def build_shot_picker() -> Table:
    """5x5 grid of buttons with no names. The goalie is drawn in the middle."""
    body = goalie_body(2, 2)
    stick = goalie_stick(2, 2)
    grid = []
    for r in range(SIZE):
        row = []
        for c in range(SIZE):
            i = r * SIZE + c
            if i in body:
                label = body[i]
            elif i in stick:
                label = stick[i]
            else:
                label = "⬜"
            row.append(Button(label, shoot, [Argument("spot", i)]))
        grid.append(row)
    return Table(grid)




@route
def index(state: State) -> Page:
    return Page(state, [
        Header("🥍 Lacrosse Shootout"),
        Text("Take " + str(ROUNDS) + " shots on a 5x5 goal. The goalie is a full body with a "
             "stick, and he learns where you like to shoot."),
        Text("Accurate shot: never misses the net, but the goalie can stretch to reach nearby spots."),
        Text("Power shot: can blow through the goalie and his stick, but edge shots may sail wide."),
        Text("Hard mode: you only get " + str(int(HARD_TIME_LIMIT)) + " seconds to shoot or you lose the shot!"),
        Text("Your name:"),
        TextBox("name", state.name),
        Text("Choose a difficulty to start:"),
        Button("Easy", start_game, [Argument("difficulty", "Easy")]),
        Button("Medium", start_game, [Argument("difficulty", "Medium")]),
        Button("Hard (Shot Clock)", start_game, [Argument("difficulty", "Hard")]),
    ])


@route
def start_game(state: State, name: str, difficulty: str) -> Page:
    state.name = name if name else "Player"
    state.difficulty = difficulty
    state.mode = "Accurate"
    state.shots_taken = 0
    state.goals = 0
    state.saves = 0
    state.misses = 0
    state.shot_counts = [0] * (SIZE * SIZE)
    state.last_shot = -1
    state.last_ar = 2
    state.last_ac = 2
    state.shot_start = time.time()
    state.message = ""
    return game(state)


@route
def set_mode(state: State, mode: str) -> Page:
    state.mode = mode
    return game(state)


@route
def game(state: State) -> Page:
    content = [
        Header("Shot " + str(state.shots_taken + 1) + " of " + str(ROUNDS)),
        Text(state.name + " | Goals: " + str(state.goals) + " | Saves: " + str(state.saves)
             + " | Misses: " + str(state.misses) + " | " + state.difficulty),
    ]

    if state.message != "":
        content.append(Text(state.message))
        if state.last_shot != -1:
            content.append(build_goal_table(state.last_shot, state.last_ar, state.last_ac))
            content.append(Text("🟠 = your shot, 🙂🟦 = goalie, 🟫 = his stick"))
        content.append(HorizontalRule())

    if state.difficulty == "Hard":
        content.append(Text("⏱️ SHOT CLOCK: you have " + str(int(HARD_TIME_LIMIT))
                            + " seconds from when this page loaded. Shoot!"))

    content.append(Text("Shot type: " + state.mode))
    if state.mode == "Accurate":
        content.append(Button("Switch to Power Shot", set_mode, [Argument("mode", "Power")]))
    else:
        content.append(Button("Switch to Accurate Shot", set_mode, [Argument("mode", "Accurate")]))

    content.append(Text("Click anywhere in the net to shoot. He'll move once you do."))
    content.append(build_shot_picker())
    return Page(state, content)


@route
def shoot(state: State, spot: int) -> Page:
    elapsed = time.time() - state.shot_start

    if state.difficulty == "Hard" and elapsed > HARD_TIME_LIMIT:
        state.shots_taken += 1
        state.misses += 1
        state.last_shot = -1
        state.message = ("⏱️ SHOT CLOCK VIOLATION! You took " + str(round(elapsed, 1))
                         + " seconds. Shot lost.")
    else:
        ar, ac = goalie_choose_anchor(state)
        body = goalie_body(ar, ac)
        stick = goalie_stick(ar, ac)
        result = resolve_shot(state, spot, body, stick)

        state.shot_counts[spot] += 1
        state.shots_taken += 1
        state.last_shot = spot
        state.last_ar = ar
        state.last_ac = ac

        if result == "save":
            state.saves += 1
            state.message = "🧤 SAVED! The goalie got his body in front of it."
        elif result == "stick":
            state.saves += 1
            state.message = "🥍 STICK SAVE! He got his stick on it!"
        elif result == "miss":
            state.misses += 1
            state.message = "💨 MISS! Your power shot sailed wide of the cage."
        else:
            state.goals += 1
            state.message = "🚨 GOAL! You found the open net!"

    state.shot_start = time.time()

    if state.shots_taken >= ROUNDS:
        return final_page(state)
    return game(state)


@route
def final_page(state: State) -> Page:
    if state.goals > state.saves + state.misses:
        verdict = "You win! 🏆"
    elif state.goals == state.saves + state.misses:
        verdict = "It's a tie!"
    else:
        verdict = "The goalie wins this one. 🧤"

    content = [
        Header("Game Over"),
        Text(state.message),
    ]
    if state.last_shot != -1:
        content.append(build_goal_table(state.last_shot, state.last_ar, state.last_ac))

    if max(state.shot_counts) > 0:
        favorite = state.shot_counts.index(max(state.shot_counts))
        fav_row, fav_col = divmod(favorite, SIZE)
        fav_text = "Your favorite spot was row " + str(fav_row + 1) + ", column " + str(fav_col + 1) + ". Mix it up next time!"
    else:
        fav_text = "You never got a shot off in time!"

    content += [
        HorizontalRule(),
        Text("Final score for " + state.name + " (" + state.difficulty + "):"),
        Text(str(state.goals) + " goals, " + str(state.saves) + " saves, " + str(state.misses) + " misses"),
        Text(verdict),
        Text(fav_text),
        Button("Play Again", index),
    ]
    return Page(state, content)


start_server(State("", "Medium", "Accurate", 0, 0, 0, 0, [0] * (SIZE * SIZE), -1, 2, 2, 0.0, ""))
