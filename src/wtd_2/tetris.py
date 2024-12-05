from enum import Enum
import math
from array import array
import random
from datetime import datetime, timedelta

# TODO:P0 Implement border limits
#   for i in range(canvasWidth):
#     game._blocks[((canvasHeight - 1) * canvasWidth) + i] = 1

class Point:
    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y

    def copy(self, pt):
        self.x = pt.x
        self.y = pt.y
      

class BlockColors:
    def __init__(self, low='', main='', high=''):
        self.low = low
        self.main = main
        self.high = high

class InputEvent(Enum):
    UNKNOWN = 0
    LEFT = 1
    RIGHT = 2
    TURN_LEFT = 3
    TURN_RIGHT = 4
    UP = 5
    DOWN = 6

class GameState(Enum):
    UNKNOWN = 0
    PLAYING = 1
    GRID_CHANGED = 2
    GAME_OVER = 3

    # /// <summary>
    # /// Yet another Tetris implementation
    # /// 
    # /// REFERENCES:
    # ///     https://tetris.wiki/Glossary
    # ///     https://tetris.com/about-us
    # ///     "Let's make 16 games in C++: TETRIS" https://www.youtube.com/watch?v=zH_omFPqMO4&t=1s
    # ///     https://tetris.com/article/35/tetris-lingo-every-player-should-know
    # /// </summary>
class TetrisGame:
    DROP_FAST_WAIT_INTERVAL_MS = 50
    DROP_NORMAL_WAIT_INTERVAL_MS = 1000

    def __init__(self, logger, width, height):
        self._logger = logger
        self._gameWidth = width
        self._gameHeight = height
        self._hasGravity = True
        self._isInverted = False
        self._animationMode = 0     # 0 = No animation, 1 = Animate current piece, 2 = Animate all
        
        # Block definitions
        self._blocks = None
        self._buffer = None
        
        self._currColorNum = 1
        self._random = random.Random()

        self._currPos = [Point() for _ in range(4)]
        self._oldPos = [Point() for _ in range(4)]

        # // Tetromino definitions.  
        # // - https://en.wikipedia.org/wiki/Tetromino
        self._tetrominos = array("i", [
            1, 3, 5, 7,  # I
            2, 4, 5, 7,  # Z
            3, 5, 4, 6,  # S
            3, 5, 4, 7,  # T
            2, 3, 5, 7,  # L
            3, 5, 7, 6,  # J
            2, 3, 4, 5,  # O
        ])

        #// Colors based on https://tetris.wiki/File:TGM_Legend_tetriminos.png
        self._tetrominoColors = [
            None,
            BlockColors("#300030", "#cc0b03", "#f67e00"),
            BlockColors("#303000", "#c85300", "#ea9300"),
            BlockColors("#001030", "#001ac1", "#0086ec"),
            BlockColors("#300030", "#8f018f", "#df16df"),
            BlockColors("#003030", "#009500", "#54e600"),
            BlockColors("#003030", "#0084b1", "#00cede"),
            BlockColors("#303000", "#967b00", "#d5c600"),
        ]

        self._lastEventMs = datetime.now()
        self._blockDropWaitIntervalMs = self.DROP_NORMAL_WAIT_INTERVAL_MS
        self._hasPositionChanged = False

        # animation
        self._currAnimIndex = 0

        self.initialize()

    def initialize(self):
        self._blocks = array("i", [0] * (self._gameWidth * self._gameHeight))
        self._buffer = array("i",[0] * (self._gameWidth * self._gameHeight))
        self._currPos = [Point() for _ in range(4)]
        self._oldPos = [Point() for _ in range(4)]

        self._hasGravity = True
        self.clear_board()
        self.select_random_tetromino()

    def get_current_tetromino(self):
        return self._currPos

    def clear_board(self):
        for i in range(len(self._blocks)):
            self._blocks[i] = 0

    def toggle_gravity(self):
        self._hasGravity = not self._hasGravity

    def toggle_luminosity(self):
        self._isInverted = not self._isInverted

    def toggle_animation(self):
        self._animationMode += 1
        if self._animationMode > 2:
            self._animationMode = 0

    def is_new_pos_valid(self):
        for i in range(4):
            if (self._currPos[i].x < 0 or self._currPos[i].x >= self._gameWidth or 
                self._currPos[i].y >= self._gameHeight):
                return False

            elif self._blocks[(self._gameWidth * self._currPos[i].y) + self._currPos[i].x] != 0:
                return False

        return True

    # Example Tetris key shortcuts https://strategywiki.org/wiki/Tetris/Controls
    def process_key_press(self, key_press):
        if key_press == 'LEFT':
            self.process_input_event(InputEvent.LEFT)
        elif key_press == 'RIGHT':
            self.process_input_event(InputEvent.RIGHT)
        elif key_press == 'UP':
            self.process_input_event(InputEvent.UP)
        elif key_press == 'DOWN':
            self.process_input_event(InputEvent.DOWN)
        elif key_press == 'z':
            self.process_input_event(InputEvent.TURN_LEFT)
        elif key_press == 'x':
            self.process_input_event(InputEvent.TURN_RIGHT)
        elif key_press == 'g':            
            # Toggle gravity, mainly for testing, not just cheating... 
            self.toggle_gravity()
        if key_press == 'i':            
            self.toggle_luminosity()
        if key_press == 'a':
            self.toggle_animation()
        if key_press == 'DELETE':
            self.initialize()


    def process_input_event(self, input_event):
        self._hasPositionChanged = True
        dx = 0
        dy = 0
        rotate = 0

        if input_event == InputEvent.LEFT:
            dx = -1
        elif input_event == InputEvent.RIGHT:
            dx = 1
        elif input_event == InputEvent.TURN_LEFT:
            rotate = -1
        elif input_event == InputEvent.TURN_RIGHT:
            rotate = 1
        elif input_event == InputEvent.DOWN:
            if self._hasGravity:
                self._blockDropWaitIntervalMs = self.DROP_FAST_WAIT_INTERVAL_MS
            else:
                dy = 1
        elif input_event == InputEvent.UP:
            dy = -1

        # Attempt to process move, revert if out of bounds, or blocked
        for i in range(4):
            self._oldPos[i].copy(self._currPos[i])
            self._currPos[i].x += dx
            self._currPos[i].y += dy

        if not self.is_new_pos_valid():
            for i in range(4):
                self._currPos[i].copy(self._oldPos[i])

        # Attempt to process rotate right
        if rotate == 1:
            pivot = self._currPos[1]  # Center of rotation
            for i in range(4):
                x = self._currPos[i].y - pivot.y
                y = self._currPos[i].x - pivot.x
                self._currPos[i].x = pivot.x - x
                self._currPos[i].y = pivot.y + y

            # Revert to old "current" position?
            if not self.is_new_pos_valid():
                for i in range(4):
                    self._currPos[i].copy(self._oldPos[i])

        # # Attempt to process rotate right
        # if rotate == -1:


    def game_tick(self):
        state = GameState.PLAYING
        now = datetime.now()

        # Flag position/grid state changed since last tick (cause UI update)
        if self._hasPositionChanged:
            state = GameState.GRID_CHANGED
            self._hasPositionChanged = False

        # Time to drop piece by one block?
        if (now - self._lastEventMs).total_seconds() * 1000 >= self._blockDropWaitIntervalMs:
            
            # Attempt to advance piece, backup current state, move down one row
            hasGravity = self._hasGravity
            for i in range(4):
                self._oldPos[i].copy(self._currPos[i])
                if hasGravity:
                    self._currPos[i].y += 1

            if not self.is_new_pos_valid():
                # Persist grid blocks with last valid position
                for i in range(4):
                  try:
                    self._blocks[(self._oldPos[i].y * self._gameWidth) + self._oldPos[i].x] = self._currColorNum
                  except Exception as e:
                    raise RuntimeError(f"Persist grid block fail, i: {i}, self._oldPos[i]: {self._oldPos[i].x}, {self._oldPos[i].y}") from e

                self.select_random_tetromino()

            self._lastEventMs = now
            self._blockDropWaitIntervalMs = self.DROP_NORMAL_WAIT_INTERVAL_MS
            state = GameState.GRID_CHANGED

        # Check for completed lines? Strategy: 'Copy' all lines, from bottom to top, overwriting completed lines.
        k = self._gameHeight - 1
        for row in range(self._gameHeight - 1, -1, -1):
            count = 0
            
            for col in range(self._gameWidth):
                if self._blocks[(row * self._gameWidth) + col] != 0:
                    count += 1
             
                self._blocks[(k * self._gameWidth) + col] = self._blocks[(row * self._gameWidth) + col]
            
            if count < self._gameWidth:
                k -= 1

        # state = GameState.GAME_OVER
        # dx = 0; rotate = 0; delay = 0.3;

        return state


    def select_random_tetromino(self):
        # Python's randint is inclusive at both ends
        self._currColorNum = random.randint(1, 7)
        
        # Adjusted for Python's 0-based indexing
        newTetrominoIndex = random.randint(0, 6)

        for i in range(4):
            self._currPos[i].x = math.floor(self._gameWidth / 2) + self._tetrominos[(newTetrominoIndex * 4) + i] % 2
            self._currPos[i].y = self._tetrominos[(newTetrominoIndex * 4) + i] // 2  # Integer division
        
        self._logger.print(f"select_random_tetromino, self._currColorNum: {self._currColorNum}, newTetrominoIndex: {newTetrominoIndex}")

    # Composite and return display buffer with background, entities, sprites, etc.. into single 
    # buffer for direct rendering
    # TODO:P0 PERF Add functions/logic to just Draw deltas instead of full buffer refresh
    
    

    def get_display_buffer(self):
        isMonochrome = True

        light = 1
        dark = 0
        if self._isInverted:
            light = 0
            dark = 1

        if self._animationMode == 0:
            curr_piece_color = light
        else:
            self._currAnimIndex += 1
            if (self._currAnimIndex > 1):
                self._currAnimIndex = 0

            curr_piece_color = self._currAnimIndex

        if self._animationMode != 2:
            block_color = light
        else:
            block_color = self._currAnimIndex 

        # Update entire buffer, while also Coalesce non zero colors to 0 or 1 Monochrome mode...
        if isMonochrome:
            self._buffer = [block_color if e != 0 else dark for e in self._blocks]


        # Overlay current tetromino
        curr_piece = self.get_current_tetromino()
        for i in range(4):
            pixelIndex = (self._gameWidth * curr_piece[i].y) + curr_piece[i].x 
            self._buffer[pixelIndex] = curr_piece_color

        return self._buffer


