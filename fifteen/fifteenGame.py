from copy import deepcopy
import math

class Board:
	"""Represents an N x N sliding puzzle board.

	- Internally stores tiles as a flat list of size N*N (0 represents the empty).
	- `positions` maps each tile value to its [row, col] coordinate (lists as requested).
	"""

	def __init__(self, tiles):
		# Accept either a flat list of ints or a nested list (list of rows).
		if not hasattr(tiles, "__iter__"):
			raise ValueError("tiles must be an iterable of ints or rows")

		# detect nested list
		if len(tiles) > 0 and isinstance(tiles[0], list):
			size = len(tiles)
			flat = [int(x) for row in tiles for x in row]
		else:
			flat = [int(x) for x in tiles]
			length = len(flat)
			size = int(math.isqrt(length))
			if size * size != length:
				raise ValueError("Flat tiles must have length that is a perfect square")

		self.size = size
		self.tiles = flat
		# positions: value -> [row, col]
		self.positions = {}
		for idx, val in enumerate(self.tiles):
			r, c = divmod(idx, self.size)
			self.positions[int(val)] = [r, c]

	def index(self, row, col):
		return row * self.size + col

	def to_list(self):
		return [self.tiles[i : i + self.size] for i in range(0, len(self.tiles), self.size)]

	def __str__(self):
		rows = self.to_list()
		width = len(str(self.size * self.size - 1))
		return "\n".join(" ".join(f"{v:{width}d}" for v in row) for row in rows)

	def copy(self):
		return Board(self.tiles.copy())

	def valid_moves(self):
		"""Return list of valid moves for the empty tile.
		Moves are: 'up', 'down', 'left', 'right'.
		
		Under the "tile moves into the blank" semantics:
		- 'up' is valid when there is a tile below the blank (it can move up)
		- 'down' is valid when there is a tile above the blank (it can move down)
		- 'left' is valid when there is a tile to the right of the blank (it can move left)
		- 'right' is valid when there is a tile to the left of the blank (it can move right)
		"""
		zero_pos = self.positions.get(0)
		if zero_pos is None:
			return []
		r, c = zero_pos
		moves = []
		if r < self.size - 1:
			moves.append("up")
		if r > 0:
			moves.append("down")
		if c < self.size - 1:
			moves.append("left")
		if c > 0:
			moves.append("right")
		return moves

	def apply_move(self, move):
		"""Return a new Board with the move applied.

		If `move` is invalid or not allowed for this board, return an unchanged copy.
		Under the "tile moves into the blank" semantics the named direction
		is the direction the tile moves (into the blank's square).
		"""
		if move not in ("up", "down", "left", "right"):
			return self

		if move not in self.valid_moves():
			return self

		new = self.copy()
		zr, zc = new.positions[0]
		# Determine source tile coordinates (the tile that will move into blank)
		if move == "up":
			sr, sc = zr + 1, zc
		elif move == "down":
			sr, sc = zr - 1, zc
		elif move == "left":
			sr, sc = zr, zc + 1
		else:  # right
			sr, sc = zr, zc - 1

		z_idx = new.index(zr, zc)
		s_idx = new.index(sr, sc)
		# swap: source tile moves into blank, blank moves to source
		new.tiles[z_idx], new.tiles[s_idx] = new.tiles[s_idx], new.tiles[z_idx]
		# update positions
		new.positions[0] = [sr, sc]
		moved_val = new.tiles[z_idx]  # tile that moved into blank
		new.positions[moved_val] = [zr, zc]

		return new

	def isterminal(self):
		"""Return True if board is in solved (terminal) state.

		Solved ordering is 1,2,3,...,N*N-1,0
		"""
		n = self.size * self.size
		for i in range(n - 1):
			if self.tiles[i] != i + 1:
				return False
		return self.tiles[-1] == 0

	def manhattan(self):
		"""Return sum of Manhattan distances of tiles from goal positions."""
		s = 0
		sz = self.size
		for idx, val in enumerate(self.tiles):
			if val == 0:
				continue
			# goal position for val
			goal_idx = val - 1
			cr, cc = divmod(idx, sz)
			gr, gc = divmod(goal_idx, sz)
			s += abs(cr - gr) + abs(cc - gc)
		return s

def apply_move(board, move):
	"""Function wrapper: takes a Board and move, returns a new Board."""
	return board.apply_move(move)


def isterminal(board):
	"""Wrapper function: returns True if `board` is terminal/solved."""
	return board.isterminal()


if __name__ == "__main__":
	# Demonstration for different sizes
	start4 = [1, 2, 3, 4,
			  5, 6, 7, 8,
			  9,10,11,12,
			  13,14,0,15]
	b4 = Board(start4)
	print("4x4 initial:\n", b4)
	print("Valid moves:", b4.valid_moves())
	nb4 = b4.apply_move('right')
	print("After moving right:\n", nb4)

	start3 = [[1,2,3],[4,5,6],[7,8,0]]
	b3 = Board(start3)
	print("\n3x3 initial:\n", b3)
	print("Valid moves:", b3.valid_moves())
