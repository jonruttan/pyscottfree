#
#	Makefile for the thing
#
CC	=	gcc
#
#
all	:	ScottCurses ScottStdio

ScottCurses.o:	ScottCurses.c Scott.h

ScottCurses:	ScottCurses.o
	$(CC) ScottCurses.o -o ScottCurses -lcurses -ltermcap

ScottStdio.o:	ScottStdio.c Scott.h

ScottStdio:	ScottStdio.o
	$(CC) ScottStdio.o -o ScottStdio

clean:
	rm -f *.o ScottCurses ScottStdio *~
