#!/usr/bin/env python

from nonblock import nonblock_read
import os
import time
import sys
import random

import tty
import termios



global origSettings

global lastMsg
lastMsg = ''

def output(msg):
    # Output - Reset the tty to the original mode, print and flush the message, then go back to raw input
    global lastMsg
    termios.tcsetattr(sys.stdin.fileno(), termios.TCSANOW, origSettings)
    sys.stdout.write(msg)
    sys.stdout.flush()
    lastMsg = msg
    tty.setraw(sys.stdin)

def printHelp():
    output('''Controls:

  Movement:
\tw = move north
\ta = move west
\ts = move south
\td = move east

  Other:
\tt = Tell current position
\tp = Poke for treasure
\tc = Check Compass
\th = Show help
''')
    sys.stdout.flush()

def drawMap(x, y, wallNorth, wallSouth, wallEast, wallWest, tries, compassRemaining, pokedSpots, monsterPos):
    termios.tcsetattr(sys.stdin.fileno(), termios.TCSANOW, origSettings)
    sys.stdout.flush()
    if os.name == 'nt':
        os.system('cls')
    else:
        os.system('clear')

    sys.stdout.write('WELCOME TO THE BOX! (h = help)\n\n')

    sys.stdout.write(('=' * (wallEast - wallWest + 2)) + '\n')
    for mapY in range(wallNorth - wallSouth, -1, -1):
        sys.stdout.write('|')
        for mapX in range(wallEast - wallWest + 1):
            # Monster on top, then you, then poked spots, then blank spot
            if [mapX, mapY] == monsterPos:
                sys.stdout.write('@')
            elif mapX == x and mapY == y:
                sys.stdout.write('*')
            elif (mapX, mapY) in pokedSpots:
                sys.stdout.write('X')
            else:
                sys.stdout.write(' ')
        sys.stdout.write('|\n')
    sys.stdout.write(('=' * (wallEast - wallWest + 2)) + '\n')
    sys.stdout.write('Pokes(p): %d\tCompass(c): %d\nPos: (%d, %d)\n%s\n\n' %(tries, compassRemaining, x, y, '-' * 20))
    sys.stdout.write('\n\n%s\n' %(lastMsg,))
    sys.stdout.flush()
    tty.setraw(sys.stdin)

if __name__ == '__main__':
    # Get original terminal settings
    origSettings = termios.tcgetattr(sys.stdin.fileno())

    # Say Hello
    output('You have entered THE BOX!\n')
    printHelp()
    output('\n')

    keepGoing = True

    # Setup bounds
    WALL_WEST = 0
    WALL_EAST = 25
    WALL_SOUTH = 0
    WALL_NORTH = 15

    # Within this many steps generates a "close" message when you poke
    VERY_CLOSE = 6

    # Start you in center of map
    x = 7
    y = 7

    # Tuples of (x, y) where we have poked in the past
    pokedSpots = []

    monsterPos = [3, 9]

    # Generate a treasure which is at any other point
    treasureX = x
    treasureY = y
    while treasureX == x and treasureY == y:
        treasureX = random.randint(WALL_WEST, WALL_EAST)
        treasureY = random.randint(WALL_SOUTH, WALL_NORTH)
    tries = 5
    compassRemaining = 9

    # Set terminal to raw input so we are in full control. This overrides the default line-buffered mode.
    tty.setraw(sys.stdin)

    # If you want to cheat
    output('Treasure is %d %d\n' % (treasureX, treasureY))

    # Monster moves every 2 seconds
    monsterSpeed = 2
    monsterTimeElapsed = 0

    # One cycle per this often
    GAME_SPEED = .5 

    lastTime = time.time()
    while keepGoing:
        # Draw the map
        drawMap(x, y, WALL_NORTH, WALL_SOUTH, WALL_EAST, WALL_WEST, tries, compassRemaining, pokedSpots, monsterPos)

        # Take the current time, and subtract from last time we were here. This gives us a constant game speed no matter what processing we do.
        now = time.time()

        # Sleep such that we retain the "one cycle per GAME_SPEED"
        time.sleep(max(GAME_SPEED - (now - lastTime), 0))

        # Increment the monster timer to see if he moves
        monsterTimeElapsed += GAME_SPEED
        lastTime = now

        if monsterTimeElapsed >= monsterSpeed:
            # Time for the monster to move.
            monsterTimeElapsed = 0
            # Monster position:  first, random between 0-10. If 0-3, will only move in x. If 4-6, will only move in y. 7-10 will move x and y.
            firstRand = random.randint(0, 10)
            if firstRand <= 3:
                moveX = True
                moveY = False
            elif firstRand <= 6:
                moveX = False
                moveY = True
            else:
                moveX = moveY = True
            if moveX is True:
                if random.randint(0, 1) == 0:
                    # Go left
                    monsterPos[0] = max(monsterPos[0] - 1, 0)
                else:
                    monsterPos[0] = min(monsterPos[0] + 1, WALL_EAST)
            if moveY is True:
                if random.randint(0, 1) == 0:
                    # Go left
                    monsterPos[1] = max(monsterPos[1] - 1, 0)
                else:
                    monsterPos[1] = min(monsterPos[1] + 1, WALL_NORTH)

        # See if we got eaten
        if monsterPos == [x, y]:
            tries = 0
            output('YOU WERE EATEN BY THE MONSTER!\n')
            keepGoing = False
            break

        # Check for any input, and process a single command.
        data = nonblock_read(sys.stdin, 1, 't')

        # We have a loop here so we can break, it will only ever have 1 element per the limit above
        for character in data:
            if character == 'q':
                tries = 0
                keepGoing = False
                break
            elif character == 'w':
                y += 1
                output('You take a step north.\n')
                if y > WALL_NORTH:
                    output('You hit the north wall!\n\n')
                    y = WALL_NORTH
            elif character == 's':
                y -= 1
                output('You take a step south.\n')
                if y < WALL_SOUTH:
                    output('You hit the south wall!\n\n')
                    y = 0
            elif character == 'a':
                x -= 1
                output('You take a step west.\n')
                if x < WALL_WEST:
                    output('You hit the west wall!\n\n')
                    x = 0
            elif character == 'd':
                x += 1
                output('You take a step east.\n')
                if x > WALL_EAST:
                    output('You hit the east wall!\n\n')
                    x = WALL_EAST
            elif character == 't':
                output('You are at: (x=%d, y=%d)\n\n' %(x, y),)
            elif character == 'h':
                printHelp()
            elif character == 'p':
                output('You poke around for treasure...\n\n')

                if x == treasureX and y == treasureY:
                    output('You found the treasure!\n\n')
                    keepGoing = False
                    break
                else:
                    output('You find nothing.\n\n')
                    tries -= 1
                    if tries < 0:
                        output('\n**** You die of exhaustion. ****\n\n')
                        keepGoing = False
                        break
                    pokedSpots.append( (x, y) )
            elif character == 'c':
                if compassRemaining <= 0:
                    output('Your compass seems used up..\n\n')
                else:
                    # Collect hint output because we only save the last message
                    hintOutput = ''
                    if abs(x - treasureX) <= VERY_CLOSE:
                        hintOutput += 'You feel very close in respect to east-west..\n\n'
                    else:
                        if x > treasureX:
                            hintOutput += 'You can feel the treasure far to the west..\n\n'
                        else:
                            hintOutput += 'You can feel the treasure far to the east..\n\n'

                    if abs(y - treasureY) <= VERY_CLOSE:
                        hintOutput += 'You feel very close in respect to north-south..\n\n'
                    else:
                        if y > treasureY:
                            hintOutput += 'You can feel the treasure far to the north..\n\n'
                        else:
                            hintOutput += 'You can feel the treasure far to the south..\n\n'
                    output(hintOutput)
            elif character == '\n':
                output('\n')


    if tries > 0:
        points = tries * compassRemaining
        output('You win with %d points! (%d tries * %d remaining compass)\n' %(points, tries, compassRemaining))
    else:
        output('You lose! GAME OVER!\n')

termios.tcsetattr(sys.stdin.fileno(), termios.TCSANOW, origSettings)
