import heapq
import time

# import Board only for typing-like handling; runtime import handled to avoid circular
try:
    from fifteenGame import Board
except Exception:
    from fifteen.fifteenGame import Board


def astar(start_board, time_limit=1.0, max_iters=200000):
    """Run A* from start_board to solved state.

    Returns a list of moves (e.g., ['up','left',...]) if solved within limits, else None.
    """
    start_time = time.time()

    start_tiles = tuple(start_board.tiles)
    start_h = start_board.manhattan()

    # priority queue: (f, g, counter, tiles_tuple, path)
    counter = 0
    pq = [(start_h, 0, counter, start_tiles, [])]
    counter += 1

    seen_g = {start_tiles: 0}

    iters = 0
    while pq:
        if time.time() - start_time > time_limit:
            return None
        iters += 1
        if iters > max_iters:
            return None

        f, g, _, tiles, path = heapq.heappop(pq)
        # reconstruct board from tiles
        board = Board(list(tiles))
        if board.isterminal():
            return path

        for move in board.valid_moves():
            nb = board.apply_move(move)
            ntiles = tuple(nb.tiles)
            ng = g + 1
            prev = seen_g.get(ntiles)
            if prev is not None and prev <= ng:
                continue
            seen_g[ntiles] = ng
            nh = nb.manhattan()
            nf = ng + nh
            heapq.heappush(pq, (nf, ng, counter, ntiles, path + [move]))
            counter += 1

    return None


def next_move_astar(start_board, time_limit=1.0):
    """Return the first move along an A* solution path, or None if not found within time_limit."""
    path = astar(start_board, time_limit=time_limit)
    if path and len(path) > 0:
        return path[0]
    return None
