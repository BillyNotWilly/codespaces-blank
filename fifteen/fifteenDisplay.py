import sys
import random
import threading
import time
import pygame

# Import modules
from fifteenGame import Board
from fifteenSolver import next_move_astar, astar, greedy_best_first


WINDOW_PADDING = 20
TILE_SIZE = 100
FONT_SIZE = 48
PANEL_WIDTH = 240

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (96, 192, 96)
GRAY = (200, 200, 200)
TEXT_COLOR = (0, 0, 0)


def scramble_board(size=4, moves=200):
    # start from solved board and apply random valid moves
    solved = list(range(1, size * size)) + [0]
    b = Board(solved)
    for _ in range(moves):
        m = random.choice(b.valid_moves())
        b = b.apply_move(m)
    return b


def load_board_from_file(filepath):
    """Load a board from a file.
    
    File format:
    - First line: board size n
    - Next n lines: n space-separated integers
    
    Returns: (Board, size) or (None, None) if file is empty or doesn't exist
    """
    try:
        with open(filepath, 'r') as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
            
        if not lines:
            return None, None
        
        # First line is the board size
        size = int(lines[0])
        
        # Next n lines should contain the board
        if len(lines) < size + 1:
            print(f"Error: Expected {size} lines of board data, got {len(lines) - 1}")
            return None, None
        
        # Parse the board
        board_data = []
        for i in range(1, size + 1):
            row = list(map(int, lines[i].split()))
            if len(row) != size:
                print(f"Error: Row {i} has {len(row)} elements, expected {size}")
                return None, None
            board_data.extend(row)
        
        # Create and return the board
        board = Board(board_data)
        return board, size
    except FileNotFoundError:
        return None, None
    except (ValueError, IndexError) as e:
        print(f"Error parsing board file: {e}")
        return None, None


HIGHLIGHT_MS = 400  # milliseconds


def _start_astar_search(board, time_limit=5.0, setter=None):
    """Run A* in a background thread and call setter(result, board_hash) when done."""
    def _worker(bcopy, tlimit, cb):
        try:
            path = astar(bcopy, time_limit=tlimit)
        except Exception:
            path = None
        board_hash = tuple(bcopy.tiles)
        if cb:
            cb(path, board_hash)

    th = threading.Thread(target=_worker, args=(board.copy(), time_limit, setter))
    th.daemon = True
    th.start()
    return th


def _start_greedy_search(board, time_limit=5.0, setter=None):
    """Run Greedy Best First Search in a background thread and call setter(result, board_hash) when done."""
    def _worker(bcopy, tlimit, cb):
        try:
            path = greedy_best_first(bcopy, time_limit=tlimit)
        except Exception:
            path = None
        board_hash = tuple(bcopy.tiles)
        if cb:
            cb(path, board_hash)

    th = threading.Thread(target=_worker, args=(board.copy(), time_limit, setter))
    th.daemon = True
    th.start()
    return th


def draw_board(screen, board, font, last_moved=None, last_move_time=0, best_move=None):
    size = board.size
    board_w = size * TILE_SIZE
    board_h = size * TILE_SIZE

    screen.fill(GRAY)

    # Highlight is active whenever last_moved is set (persist until next move)
    highlight_active = last_moved is not None

    # compute blank pos and source coords for best_move highlighting
    blank_pos = board.positions.get(0)
    best_source = None
    if best_move and blank_pos is not None:
        zr, zc = blank_pos
        if best_move == 'up':
            best_source = (zr + 1, zc)
        elif best_move == 'down':
            best_source = (zr - 1, zc)
        elif best_move == 'left':
            best_source = (zr, zc + 1)
        elif best_move == 'right':
            best_source = (zr, zc - 1)

    for r in range(size):
        for c in range(size):
            idx = board.index(r, c)
            val = board.tiles[idx]

            # determine color: empty = GRAY, correct position = GREEN, else WHITE
            expected = (r * size + c + 1) if not (r == size - 1 and c == size - 1) else 0
            if val == 0:
                color = GRAY
                text_color = WHITE
            elif val == expected:
                color = GREEN
                text_color = BLACK
            else:
                color = WHITE
                text_color = BLACK

            # apply highlight if this is the tile that just moved
            if highlight_active and last_moved == (r, c) and val != 0:
                # brighten green tiles slightly, darken white tiles slightly
                if color == GREEN:
                    color = tuple(min(255, x + 30) for x in color)
                else:
                    color = tuple(int(x * 0.85) for x in color)

            # apply best-move highlight: use distinct blue tint for the suggested tile
            if best_source == (r, c) and val != 0:
                color = (100, 160, 255)
                text_color = BLACK

            x = WINDOW_PADDING + c * TILE_SIZE
            y = WINDOW_PADDING + r * TILE_SIZE
            rect = pygame.Rect(x, y, TILE_SIZE - 2, TILE_SIZE - 2)
            pygame.draw.rect(screen, color, rect)

            if val != 0:
                text = font.render(str(val), True, text_color)
                text_rect = text.get_rect(center=rect.center)
                screen.blit(text, text_rect)


def main():
    pygame.init()
    pygame.display.set_caption("15-Puzzle")

    # Check if a board file is provided as command-line argument
    board = None
    size = 4
    if len(sys.argv) > 1:
        board, size = load_board_from_file(sys.argv[1])
    
    # If no file was provided or file was empty, create a random 4x4 board
    if board is None:
        size = 4
        board = scramble_board(size=size, moves=300)
    
    # Keep a copy of the starting scrambled board so we can reset to it
    start_board = board.copy()
    # history stores previous boards so we can undo moves
    history = []

    # astar search state (async)
    search_in_progress = False
    search_thread = None
    search_path = None  # list of moves if found
    search_board_hash = None  # tuple(board.tiles) for which search was run
    search_start_time = None  # time when search was started
    search_elapsed_time = None  # elapsed time when search completed
    search_type = None  # 'astar' or 'greedy'
    auto_run_mode = False
    auto_run_index = 0
    auto_run_interval_ms = 600
    last_auto_step_time = 0

    win_w = size * TILE_SIZE + WINDOW_PADDING * 2 + PANEL_WIDTH
    win_h = size * TILE_SIZE + WINDOW_PADDING * 2
    screen = pygame.display.set_mode((win_w, win_h))
    font = pygame.font.SysFont(None, FONT_SIZE)

    clock = pygame.time.Clock()
    last_moved = None
    last_move_time = 0
    moves_count = 0
    solver_cached = None
    solver_board_hash = None
    cached_cur_h = None
    cached_neigh_h = None
    cached_board_hash = None
    draw_board(screen, board, font, last_moved, last_move_time)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                    break

                # Undo last move
                if event.key == pygame.K_u:
                    # cancel any pending confirm or running auto-run
                    auto_run_mode = False
                    if history:
                        board = history.pop()
                        moves_count = max(0, moves_count - 1)
                        last_moved = None
                        last_move_time = pygame.time.get_ticks()
                        solver_board_hash = None
                    continue

                # Reset board to starting scrambled position
                if event.key == pygame.K_r:
                    # cancel search and auto-run
                    auto_run_mode = False
                    search_in_progress = False
                    board = start_board.copy()
                    history.clear()
                    moves_count = 0
                    last_moved = None
                    last_move_time = pygame.time.get_ticks()
                    solver_board_hash = None
                    search_path = None
                    search_board_hash = None
                    continue

                # New random board
                if event.key == pygame.K_n:
                    # cancel search and auto-run
                    auto_run_mode = False
                    search_in_progress = False
                    board = scramble_board(size=size, moves=300)
                    start_board = board.copy()  # update start_board so reset goes to this new board
                    history.clear()
                    moves_count = 0
                    last_moved = None
                    last_move_time = pygame.time.get_ticks()
                    solver_board_hash = None
                    search_path = None
                    search_board_hash = None
                    continue
                if event.key == pygame.K_s:
                    if not search_in_progress:
                        # start async search
                        search_in_progress = True
                        search_path = None
                        search_board_hash = tuple(board.tiles)
                        search_start_time = time.time()
                        search_elapsed_time = None
                        search_type = 'astar'

                        def _setter(result, bh):
                            nonlocal search_in_progress, search_path, search_board_hash, search_elapsed_time, search_start_time
                            search_in_progress = False
                            search_path = result
                            search_board_hash = bh
                            if search_start_time is not None:
                                search_elapsed_time = time.time() - search_start_time

                        search_thread = _start_astar_search(board, time_limit=10.0, setter=_setter)
                    continue

                # start Greedy Best First search for full solution
                if event.key == pygame.K_g:
                    if not search_in_progress:
                        # start async search
                        search_in_progress = True
                        search_path = None
                        search_board_hash = tuple(board.tiles)
                        search_start_time = time.time()
                        search_elapsed_time = None
                        search_type = 'greedy'

                        def _setter(result, bh):
                            nonlocal search_in_progress, search_path, search_board_hash, search_elapsed_time, search_start_time
                            search_in_progress = False
                            search_path = result
                            search_board_hash = bh
                            if search_start_time is not None:
                                search_elapsed_time = time.time() - search_start_time

                        search_thread = _start_greedy_search(board, time_limit=10.0, setter=_setter)
                    continue

                # Run solution with SPACE
                if event.key == pygame.K_SPACE:
                    # if a solution is cached and it applies to current board, run it
                    if search_path is not None:
                        # require the solution to be for current board
                        if tuple(board.tiles) == search_board_hash:
                            # start auto-run immediately
                            auto_run_mode = True
                            auto_run_index = 0
                            last_auto_step_time = pygame.time.get_ticks()
                    continue

                # cancel pending confirm
                if event.key == pygame.K_c:
                    continue

                move = None
                if event.key == pygame.K_LEFT:
                    move = 'left'
                elif event.key == pygame.K_RIGHT:
                    move = 'right'
                elif event.key == pygame.K_UP:
                    move = 'up'
                elif event.key == pygame.K_DOWN:
                    move = 'down'

                if move is not None:
                    # Only highlight/apply if move is valid
                    if move in board.valid_moves():
                        # push current board onto history so we can undo back to it
                        history.append(board.copy())

                        zr, zc = board.positions[0]
                        # compute the coordinate of the tile that will move into blank
                        if move == 'up':
                            moved_coord = (zr + 1, zc)
                        elif move == 'down':
                            moved_coord = (zr - 1, zc)
                        elif move == 'left':
                            moved_coord = (zr, zc + 1)
                        else:
                            moved_coord = (zr, zc - 1)

                        # apply_move returns a new Board; update our board reference
                        board = board.apply_move(move)

                        last_moved = moved_coord
                        last_move_time = pygame.time.get_ticks()
                        moves_count += 1
                    else:
                        # invalid move -> no-op
                        pass

        # show solved state subtly (optional)
        if board.isterminal():
            pygame.display.set_caption("15-Puzzle — Solved!")
        else:
            pygame.display.set_caption("15-Puzzle")

        # compute heuristics and best move (run solver with short timeout when board changed)
        board_hash = tuple(board.tiles)
        if board_hash != cached_board_hash:
            cached_board_hash = board_hash
            cached_cur_h = board.manhattan()
            cached_neigh_h = {}
            for m in ['up','down','left','right']:
                if m in board.valid_moves():
                    nb = board.apply_move(m)
                    cached_neigh_h[m] = nb.manhattan()

        cur_h = cached_cur_h
        neigh_h = cached_neigh_h

        board_hash = tuple(board.tiles)
        if board_hash != solver_board_hash:
            solver_board_hash = board_hash
            solver_cached = next_move_astar(board, time_limit=0.2)

        best_move = solver_cached

        # handle auto-run execution if active
        if auto_run_mode and search_path and auto_run_index < len(search_path):
            now = pygame.time.get_ticks()
            if now - last_auto_step_time >= auto_run_interval_ms:
                # apply next move
                mv = search_path[auto_run_index]
                if mv in board.valid_moves():
                    history.append(board.copy())
                    zr, zc = board.positions[0]
                    if mv == 'up':
                        moved_coord = (zr + 1, zc)
                    elif mv == 'down':
                        moved_coord = (zr - 1, zc)
                    elif mv == 'left':
                        moved_coord = (zr, zc + 1)
                    else:
                        moved_coord = (zr, zc - 1)

                    board = board.apply_move(mv)
                    last_moved = moved_coord
                    last_move_time = now
                    moves_count += 1
                else:
                    # solution no longer valid
                    auto_run_mode = False
                    search_path = None
                auto_run_index += 1
                last_auto_step_time = now

            # finished
            if auto_run_index >= len(search_path):
                auto_run_mode = False
                search_path = None

        draw_board(screen, board, font, last_moved, last_move_time, best_move)

            # draw info panel on right side
        panel_x = WINDOW_PADDING + board.size * TILE_SIZE + 10
        panel_y = WINDOW_PADDING
        panel_rect = pygame.Rect(panel_x, panel_y, PANEL_WIDTH - 20, board.size * TILE_SIZE)
        pygame.draw.rect(screen, (230,230,230), panel_rect)
        pygame.draw.rect(screen, (200,200,200), panel_rect, 2)

        info_x = panel_x + 10
        y = panel_y + 8
        small = pygame.font.SysFont(None, 20)

        # summary lines
        text = small.render(f"Moves: {moves_count}", True, (0,0,0))
        screen.blit(text, (info_x, y)); y += 24
        text = small.render(f"h: {cur_h}", True, (0,0,0))
        screen.blit(text, (info_x, y)); y += 28

        # per-move heuristics
        best = best_move
        for m in ['up','down','left','right']:
            if m in neigh_h:
                marker = ' <- best' if best == m else ''
                txt = f"{m}: h={neigh_h[m]}{marker}"
            else:
                txt = f"{m}: -"
            text = small.render(txt, True, (0,0,0))
            screen.blit(text, (info_x, y))
            y += 20

        # A* best move hint (single-step suggestion)
        astar_hint = 'none' if solver_cached is None else solver_cached
        text = small.render(f"A* best: {astar_hint}", True, (0,0,0))
        screen.blit(text, (info_x, y)); y += 22

        # search status / solution info
        if search_in_progress:
            type_str = search_type.upper() if search_type else "A*"
            text = small.render(f"{type_str}: searching...", True, (200,0,0))
            screen.blit(text, (info_x, y)); y += 22
        elif search_path is not None:
            type_str = search_type.upper() if search_type else "A*"
            time_str = f" ({search_elapsed_time:.2f}s)" if search_elapsed_time is not None else ""
            if tuple(board.tiles) == search_board_hash:
                text = small.render(f"{type_str} found: {len(search_path)} moves{time_str}", True, (0,120,0))
            else:
                text = small.render(f"{type_str} found (stale): {len(search_path)} moves{time_str}", True, (120,120,0))
            screen.blit(text, (info_x, y)); y += 22
            text = small.render("Press SPACE to run solution", True, (0,0,0))
            screen.blit(text, (info_x, y)); y += 22
        else:
            text = small.render("Solver: no solution cached", True, (0,0,0))
            screen.blit(text, (info_x, y)); y += 22

        # controls hint
        text = small.render("u: undo  r: reset  n: new  s: search", True, (0,0,0))
        screen.blit(text, (info_x, y))
        y += 24

        pygame.display.flip()

        clock.tick(30)

    pygame.quit()
    sys.exit(0)

if __name__ == '__main__':
    main()