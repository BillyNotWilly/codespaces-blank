import heapq
import time

# import Board
from fifteenGame import Board


def astar(start_board, time_limit=1.0, max_iters=1000000):
    """Run A* from start_board to solved state.

    Returns a list of moves (e.g., ['up','left',...]) if solved within limits, else None.
    """
    start_time = time.time()

    start_tiles = tuple(start_board.tiles)
    start_h = start_board.manhattan() + linear_conflict(start_board)

    # priority queue: (f, g, counter, tiles_tuple)
    counter = 0
    pq = [(start_h, 0, counter, start_tiles)]
    counter += 1

    came_from = {start_tiles: None}
    g_score = {start_tiles: 0}

    iters = 0
    while pq:
        if time.time() - start_time > time_limit:
            return None
        iters += 1
        if iters > max_iters:
            return None

        f, g, _, tiles = heapq.heappop(pq)
        board = Board(list(tiles))
        if board.isterminal():
            # Reconstruct path
            path = []
            current = tiles
            while current != start_tiles:
                prev_tiles = came_from[current]
                if prev_tiles is None:
                    break
                # Find the move that led here
                prev_board = Board(list(prev_tiles))
                for move in prev_board.valid_moves():
                    if tuple(prev_board.apply_move(move).tiles) == current:
                        path.append(move)
                        break
                current = prev_tiles
            path.reverse()
            return path

        for move in board.valid_moves():
            nb = board.apply_move(move)
            ntiles = tuple(nb.tiles)
            ng = g + 1
            if ntiles not in g_score or ng < g_score[ntiles]:
                g_score[ntiles] = ng
                nh = nb.manhattan() + linear_conflict(nb)
                nf = ng + nh
                heapq.heappush(pq, (nf, ng, counter, ntiles))
                counter += 1
                came_from[ntiles] = tiles

    return None


def linear_conflict(board):
    """Calculate linear conflict heuristic."""
    conflict = 0
    size = board.size
    for row in range(size):
        tiles_in_row = []
        for col in range(size):
            val = board.tiles[row * size + col]
            if val != 0:
                goal_row = (val - 1) // size
                if goal_row == row:
                    tiles_in_row.append((val, col))
        # Count inversions in this row
        for i in range(len(tiles_in_row)):
            for j in range(i + 1, len(tiles_in_row)):
                if tiles_in_row[i][0] > tiles_in_row[j][0]:
                    conflict += 2  # Each inversion adds 2 to heuristic
    # Similarly for columns
    for col in range(size):
        tiles_in_col = []
        for row in range(size):
            val = board.tiles[row * size + col]
            if val != 0:
                goal_col = (val - 1) % size
                if goal_col == col:
                    tiles_in_col.append((val, row))
        for i in range(len(tiles_in_col)):
            for j in range(i + 1, len(tiles_in_col)):
                if tiles_in_col[i][0] > tiles_in_col[j][0]:
                    conflict += 2
    return conflict

def next_move_astar(start_board, time_limit=1.0):
    """Return the first move along an A* solution path, or None if not found within time_limit."""
    path = astar(start_board, time_limit=time_limit)
    if path and len(path) > 0:
        return path[0]
    return None


def greedy_best_first(start_board, time_limit=1.0, max_iters=1000000):
    """Run Greedy Best First Search from start_board to solved state.

    Returns a list of moves (e.g., ['up','left',...]) if solved within limits, else None.
    """
    start_time = time.time()

    start_tiles = tuple(start_board.tiles)
    start_h = start_board.manhattan() + linear_conflict(start_board)

    # priority queue: (h, counter, tiles_tuple)
    counter = 0
    pq = [(start_h, counter, start_tiles)]
    counter += 1

    came_from = {start_tiles: None}
    g_score = {start_tiles: 0}  # still track g for path reconstruction, but not used in priority

    iters = 0
    while pq:
        if time.time() - start_time > time_limit:
            return None
        iters += 1
        if iters > max_iters:
            return None

        h, _, tiles = heapq.heappop(pq)
        board = Board(list(tiles))
        if board.isterminal():
            # Reconstruct path
            path = []
            current = tiles
            while current != start_tiles:
                prev_tiles = came_from[current]
                if prev_tiles is None:
                    break
                # Find the move that led here
                prev_board = Board(list(prev_tiles))
                for move in prev_board.valid_moves():
                    if tuple(prev_board.apply_move(move).tiles) == current:
                        path.append(move)
                        break
                current = prev_tiles
            path.reverse()
            return path

        for move in board.valid_moves():
            nb = board.apply_move(move)
            ntiles = tuple(nb.tiles)
            ng = g_score[tiles] + 1
            if ntiles not in g_score or ng < g_score[ntiles]:
                g_score[ntiles] = ng
                nh = nb.manhattan() + linear_conflict(nb)
                heapq.heappush(pq, (nh, counter, ntiles))
                counter += 1
                came_from[ntiles] = tiles

    return None


def next_move_greedy(start_board, time_limit=1.0):
    """Return the first move along a Greedy Best First solution path, or None if not found within time_limit."""
    path = greedy_best_first(start_board, time_limit=time_limit)
    if path and len(path) > 0:
        return path[0]
    return None