#!/usr/bin/env python

import os
import sys
import struct
from PIL import Image, ImageDraw


def error(errno=0, string='Error'):
    sys.stderr.write(string + '\n')
    sys.exit(errno)


class SagaGfx:
    STATE_ERR = -1
    STATE_NONE = 0
    STATE_INIT = 1
    STATE_INFO = 2
    STATE_OFFSET = 3
    STATE_LOGIC = 4
    STATE_DATA = 5
    STATE_OK = 6

    LOC_ROOM = 1
    LOC_INVENTORY = 2
    LOC_ROOM_OR_INVENTORY = 3
    LOC_NOT_ROOM = 81
    LOC_NOT_INVENTORY = 82
    LOC_NOT_ROOM_OR_INVENTORY = 3


    PIC = 8
    COC = 7
    OVL = 6
    ANI = 5
    GOT = 4
    MOVE = 0xc0
    FILL = 0xc1
    NEWPIC = 0xff

    def __init__(self, path=None):
        self.state = SagaGfx.STATE_NONE
        self.file = None
        self.size = None
        self.num_rooms = None
        self.num_action89 = None
        self.num_room_exts = None
        self.offsets = None
        self.logic = None
        self.images = None
        self.palette = None
        self.state = SagaGfx.STATE_INIT

        if path is not None:
            self.open(path)

    def open(self, path):
        if self.state > SagaGfx.STATE_INIT:
            self.file.close()

        self.file = open(path, 'rb')
        self.state = SagaGfx.STATE_INFO

    def is_line_drawings(self):
        # Use darkness pic offset as LDP Flag
        return self.offsets[0] == 0

    # Info Hunk
    def read_info(self):
        if self.state is not SagaGfx.STATE_INFO:
            return False

        # Width and Height in pixels
        self.size = (
            struct.unpack('>h', self.file.read(2))[0],
            struct.unpack('>h', self.file.read(2))[0]
        )

        # Number of rooms (+1 if showPIC starts with 0)
        self.num_rooms = struct.unpack('>B', self.file.read(1))[0]

        # Number of Action89 images
        self.num_action89 = struct.unpack('>B', self.file.read(1))[0]

        # Number of extended (conditional) room images
        self.num_extended = struct.unpack('>B', self.file.read(1))[0]

        self.state += 1

        print("Size: %s" % str(self.size))
        print("Rooms: %d" % self.num_rooms)
        print("Action89 Rooms: %d" % self.num_action89)
        print("Extended Rooms: %d" % self.num_extended)

        return self

    # Offset Hunk
    def read_offset(self):
        if self.state is not SagaGfx.STATE_OFFSET:
            return self

        count = struct.unpack('>B', self.file.read(1))[0]
        self.offsets = []
        for _ in range(0, count):
            self.offsets.append(struct.unpack('>i', b'\0' + self.file.read(3))[0])

        self.state += 1

        print("Offsets: %d (%s)" % (len(self.offsets), str(self.offsets)))
        print("Line Drawing: %s" % (self.is_line_drawings() and 'Yes' or 'No'))

        return self

    # Logic Hunk
    def read_logic(self):
        if self.state is not SagaGfx.STATE_LOGIC:
            return self

        print("Tell %d" % self.file.tell())
        count = struct.unpack('>h', self.file.read(2))[0]
        self.logic = {}
        while count:
            room = struct.unpack('>B', self.file.read(1))[0]
            ppr = struct.unpack('>B', self.file.read(1))[0]
            count -= 2
            logic = dict(ppr=ppr, what=[], loc=[], obj=[], pnr=[])
            for i in range(0, ppr):
                w = struct.unpack('>B', self.file.read(1))[0]
                count -= 1
                logic['what'].append(w)

                kk = w - 80
                while kk < 0:
                    kk += 10
                loc = []
                obj = []
                for k in range(0, kk):
                    loc.append(struct.unpack('>B', self.file.read(1))[0])
                    obj.append(struct.unpack('>B', self.file.read(1))[0])
                    count -= 2

                logic['loc'].append(loc)
                logic['obj'].append(obj)

                logic['pnr'].append(struct.unpack('>B', self.file.read(1))[0])
                count -= 1

            self.logic[room] = logic

        self.state += 1

        print("Logic: %s" % self.logic)

        return self

    def get_image_id(self, saga, id):
        if self.state <= SagaGfx.STATE_LOGIC or id not in self.logic:
            return id

        for i in range(0, self.logic[id]['ppr']):
            ii = self.logic[id]['what'][i] - 80
            while ii < 0:
                ii += 10
            yes = 0
            for j in range(0, ii):
                loc = self.logic[id]['loc'][i][j]
                obj = self.logic[id]['obj'][i][j]

                if loc == SagaGfx.LOC_ROOM:
                    if saga.items[obj].location is saga.player_room:
                        yes += 1
                elif loc == SagaGfx.LOC_INVENTORY:
                    if saga.items[obj].location is 255:
                        yes += 1
                elif loc == SagaGfx.LOC_INVENTORY:
                    if saga.items[obj].location in (saga.player_room, 255):
                        yes += 1
                elif loc == SagaGfx.LOC_NOT_ROOM:
                    if saga.items[obj].location is not saga.player_room:
                        yes += 1
                elif loc == SagaGfx.LOC_NOT_INVENTORY:
                    if saga.items[obj].location is not 255:
                        yes += 1
                elif loc == SagaGfx.LOC_NOT_INVENTORY:
                    if saga.items[obj].location not in (saga.player_room, 255):
                        yes += 1

            if yes >= ii:
                pnr = self.logic[id]['pnr'][i]
                if pnr is 0:  # No picture
                    id = None
                    break
                elif pnr is 255:  # Do nothing
                    break

                # Last pic

                action = int(self.logic[id]['what'][i] / 10)
                if action is SagaGfx.PIC:
                    id = pnr
                elif action is SagaGfx.COC:
                    print('colour cycling, not implemented yet')
                elif action is SagaGfx.OVL:
                    print('overlay image, not implemented yet')
                elif action is SagaGfx.ANI:
                    print('animation, not implemented yet')
                elif action is SagaGfx.GOT:
                    print('GO_TREE for "Robin of Sherwood", not implemented yet')

        return id

    # Line Drawing
    def read_next_line_drawing(self, index):
        if self.palette is None:
            self.palette = []
            colours = struct.unpack('>B', self.file.read(1))[0]
            # print('Palette Size %d' % colours)
            for i in range(0, colours):
                r, g, b = (
                    struct.unpack('>B', self.file.read(1))[0],
                    struct.unpack('>B', self.file.read(1))[0],
                    struct.unpack('>B', self.file.read(1))[0]
                )
                # print('Palette %d: (%x %x %x)' % (i, r, g, b))
                self.palette.extend((r, g, b))
            # pprint(palette)

            # Image 0 is darkness (black)
            # NOTE: Palette entry 0 is assumed to be black
            image = Image.new('P', self.size, 0)
            image.putpalette(self.palette)
            self.images.append(image)

        magic = struct.unpack('>B', self.file.read(1))[0]
        if magic is not SagaGfx.NEWPIC:
            print('Wanted NEWPIC (0x%x), got 0x%x' % (SagaGfx.NEWPIC, magic))
            # error(1, 'Wanted NEWPIC (0x%x), got 0x%x' % (SagaGfx.NEWPIC, magic))
            return

        i = struct.unpack('>B', self.file.read(1))[0]
        if i is not index:
            error(1, 'Wanted image %d, got %d' % (index, i))
            return

        colour = struct.unpack('>B', self.file.read(1))[0]
        # print('Background colour: %d (0x%x)' % (colour, COLOURS[colour]))

        image = Image.new('P', self.size, colour)
        image.putpalette(self.palette)
        draw = ImageDraw.Draw(image)

        colour = colour == 0 and 7 or 0

        x1, y1 = 0, 0
        while True:
            command = struct.unpack('>B', self.file.read(1))[0]
            if command is SagaGfx.NEWPIC:
                self.file.seek(self.file.tell() - 1)
                break

            if command is SagaGfx.MOVE:
                y1 = struct.unpack('>B', self.file.read(1))[0]
                x1 = struct.unpack('>B', self.file.read(1))[0]
                # print('Move: (%d, %d)' % (x1, y1))
            elif command is SagaGfx.FILL:
                colour = struct.unpack('>B', self.file.read(1))[0]
                y2 = struct.unpack('>B', self.file.read(1))[0]
                x2 = struct.unpack('>B', self.file.read(1))[0]
                # print('Fill: %d @ (%d, %d)' % (colour, x2, y2))
                ImageDraw.floodfill(image, (x2, y2), colour)
            else:
                x2 = struct.unpack('>B', self.file.read(1))[0]
                y2 = command
                # print('Draw: %d @ %s %s' % (colour, (x1, y1), (x2, y2)))
                draw.line((x1, y1, x2, y2), fill=colour)
                x1, y1 = x2, y2

        # image.show()

        # pprint(list(image.getdata()))
        self.images.append(image)

    def read_next_bitmap(self):
        palette = []
        ncol = struct.unpack('>B', self.file.read(1))[0]
        for _ in range(0, ncol):
            palette.extend((
                    struct.unpack('>B', self.file.read(1))[0],
                    struct.unpack('>B', self.file.read(1))[0],
                    struct.unpack('>B', self.file.read(1))[0],
                ))
        # pprint(palette)

        data_size = struct.unpack('>h', self.file.read(2))[0]
        size = self.size[0] * self.size[1]
        bitmap = [0] * size
        i = 0
        while i < size:
            byte = self.file.read(1)
            if len(byte) != 1:
                break
            n = struct.unpack('>B', byte)[0]
            if n < 128:
                j = 1
                bitmap[i] = n
            else:
                j = n - 128
                n = struct.unpack('>B', self.file.read(1))[0]
                bitmap[i:i+j] = [n] * j
            i += j

        # pprint(bitmap)
        bytes = ''.join(chr(x) for x in bitmap).encode()
        image = Image.frombytes('P', self.size, bytes)
        image.putpalette(palette)

        # pprint(list(image.getdata()))
        self.images.append(image)

    # Data Hunk
    def read_data(self):
        if self.state is not SagaGfx.STATE_DATA:
            return self

        self.images = []
        for offset in range(0, len(self.offsets)):
            # If a room has no picture, offset is set to zero.
            if self.offsets[offset] is 0:
                continue

            print("Reading item %d" % offset)

            if self.file.tell() != self.offsets[offset]:
                print("tell %d should be %d adjusting..." %
                      (self.file.tell(), self.offsets[offset]))
                self.file.seek(self.offsets[offset])

            if self.is_line_drawings():
                self.read_next_line_drawing(offset)

            else:
                self.read_next_bitmap()

        self.state += 1

        return self

    def read(self, path=None):
        return self.read_info() \
                .read_offset() \
                .read_logic() \
                .read_data()
