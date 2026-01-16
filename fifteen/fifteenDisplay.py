import sys
import random
import pygame

# Try importing Board from the local module
try:
    from fifteenGame import Board
    from fifteenSolver import next_move_astar
except Exception:
    from fifteen.fifteenGame import Board
    from fifteen.fifteenSolver import next_move_astar


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


HIGHLIGHT_MS = 400  # milliseconds


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

    size = 4
    board = scramble_board(size=size, moves=300)
    # Keep a copy of the starting scrambled board so we can reset to it
    start_board = board.copy()
    # history stores previous boards so we can undo moves
    history = []

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
                    if history:
                        board = history.pop()
                        moves_count = max(0, moves_count - 1)
                        last_moved = None
                        last_move_time = pygame.time.get_ticks()
                        solver_board_hash = None
                    continue

                # Reset board to starting scrambled position
                if event.key == pygame.K_r:
                    board = start_board.copy()
                    history.clear()
                    moves_count = 0
                    last_moved = None
                    last_move_time = pygame.time.get_ticks()
                    solver_board_hash = None
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
        cur_h = board.manhattan()
        neigh_h = {}
        for m in ['up','down','left','right']:
            if m in board.valid_moves():
                nb = board.apply_move(m)
                neigh_h[m] = nb.manhattan()

        board_hash = tuple(board.tiles)
        if board_hash != solver_board_hash:
            solver_board_hash = board_hash
            solver_cached = next_move_astar(board, time_limit=0.5)

        best_move = solver_cached

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

        # controls hint
        text = small.render("u: undo  r: reset", True, (0,0,0))
        screen.blit(text, (info_x, y))
        y += 24

        pygame.display.flip()

        clock.tick(30)

    pygame.quit()
    sys.exit(0)


if __name__ == '__main__':
    main()
