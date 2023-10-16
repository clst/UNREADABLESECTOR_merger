#!/usr/bin/python3
import os, sys, time
import argparse

badsector_marker = b"UNREADABLESECTOR"
sectsize = 512

if sys.platform == "win32":
    from colorama import just_fix_windows_console
    just_fix_windows_console()

AsciiEscapeCode = '\033'
class colors: # You may need to change color settings
    RED = f'{AsciiEscapeCode}[31m'
    NORMAL = f'{AsciiEscapeCode}[0m'
    GREEN = f'{AsciiEscapeCode}[32m'
    YELLOW = f'{AsciiEscapeCode}[33m'
    BLUE = f'{AsciiEscapeCode}[94m'
    WHITE = f'{AsciiEscapeCode}[97m'
    GRAY = f'{AsciiEscapeCode}[37m'
colors.DEFAULT = colors.WHITE

parser = argparse.ArgumentParser(
  formatter_class=argparse.RawDescriptionHelpFormatter,
  description = f'{colors.DEFAULT}Tool to merge sector dumps.\r\n\r\nIf a sector in file 1 contains "{badsector_marker}"\n' +
    'The sector from file 2 will be used.\n' +
    f'If that one also contains "{badsector_marker}" an error will be logged.{colors.NORMAL}\n' +
    'Remember to properly quote filenames.')
parser.add_argument('f1', metavar='File1',
  type=argparse.FileType('rb'),
  help='the filename of the first dump.')
parser.add_argument('f2', metavar='File2',
  type=argparse.FileType('rb'),
  help='the filename of the second dump.')
parser.add_argument('fout', metavar='FileOut',
  type=str,
  help='the filename of the merged output file.')
parser.add_argument('-s', '--skipsect', metavar='Sectors',
  type=int,
  default=0,
  help='Skip this amount of sectors in file 1. Start from there. File 2 may be smaller than file 1. Sectors equals the first sector present in file 2.')
parser.add_argument('-a', '--enable-append', action='store_true',
  help='Allow file 2 to be larger than file 1 + skipsect. This will append the rest of file 2 to FileOut.')
parser.add_argument('-q', '--quiet', action='store_true',
  help='Do not announce file 2 bad sectors that do not exist in file 1. Also do not notify about bad sectors in skipped/copied areas.')

args = parser.parse_args()

f1 = args.f1
f2 = args.f2
fo = open(args.fout, "wb")

if os.path.isfile(args.fout) and os.stat(args.fout).st_size > 0:
    print("Error: output file exists.")
    raise FileExistsError
if not args.enable_append and args.skipsect == 0 and os.stat(f1.name).st_size != os.stat(f2.name).st_size:
    print("Error: files 1 and 2 are not the same size")
    raise AssertionError
if not args.enable_append and args.skipsect > 0 and os.stat(f1.name).st_size < os.stat(f2.name).st_size + args.skipsect*sectsize:
    print("Error: file 2 does not fit into file 1")
    raise AssertionError

def statusline(i):
    sys.stdout.write('\r{} sectors {:.3f} MB processed'.format(i, i/mb))
def badsect(i, text = 'bad  sector', ignored = False):
    if ignored:
        sys.stdout.write(colors.GRAY)
    else:
        sys.stdout.write(colors.RED)
    sys.stdout.write('\r%s %8d offset: %10s - ' % (text, i, hex(i*sectsize)))
    sys.stdout.write(colors.DEFAULT)

i = 1

stats_f1bad = 0
stats_f2bad = 0
stats_fbbad = 0
stats_fixed = 0
sect1_done = False
sect2_done = False

#kb = 1024
kb = 2
mb = kb * 1024

print(f'{colors.DEFAULT}\nFile Merge Tool v0.71 2023-09-19 by Claudius "Joe Cool" Steinhauser\n')

if args.skipsect > 0:
    print(f"{colors.BLUE}Skipping to offset {hex(args.skipsect*sectsize):10}{colors.DEFAULT}")
    #f1.seek(args.skipsect*sectsize)

while (sect1 := f1.read(sectsize)) or args.enable_append:
    if not sect1_done and len(sect1) == 0:
            sys.stdout.write(colors.BLUE)
            sys.stdout.write("\rdone reading file 1                   \n")
            badsect(i, "done sector", ignored=True)
            sys.stdout.write('copying the rest of file 2\n')
            sys.stdout.write(colors.DEFAULT)
            sect1_done = True
    if sect2_done or i <= args.skipsect:
        if sect1[0:len(badsector_marker)] == badsector_marker:
            if not args.quiet:
                badsect(i, ignored=True)
                sys.stdout.write('already in file 1\n')
            stats_f1bad+= 1
    else:
        sect2 = f2.read(sectsize)
        if len(sect2) == 0:
            sys.stdout.write(colors.BLUE)
            sys.stdout.write("\rdone reading file 2                   \n")
            badsect(i, "done sector", ignored=True)
            if sect1_done:
                sys.stdout.write('finished\n')
            else:
                sys.stdout.write('copying the rest of file 1\n')
            sys.stdout.write(colors.DEFAULT)
            sect2_done = True
        if sect1[0:len(badsector_marker)] == badsector_marker:
            stats_f1bad+= 1
            if sect2[0:len(badsector_marker)] == badsector_marker:
                badsect(i)
                sys.stdout.write(colors.RED)
                sys.stdout.write('also bad in file 2\n')
                sys.stdout.write(colors.DEFAULT)
                stats_fbbad+= 1
                stats_f2bad+= 1
            elif sect2_done:
                if not args.quiet:
                    badsect(i, ignored=True)
                    sys.stdout.write('already in file 2\n')
                stats_f2bad+= 1
                stats_fbbad+= 1
            else:
                badsect(i, ignored=True)
                sys.stdout.write(colors.GREEN)
                sys.stdout.write('using file 2 instead\n')
                sys.stdout.write(colors.DEFAULT)
                stats_fixed+= 1
                fo.write(sect2)
                i+=1
                continue
        elif not sect2_done and sect2[0:len(badsector_marker)] == badsector_marker:
            if not args.quiet:
                badsect(i, "file2 bad  ", ignored=True)
                sys.stdout.write('using file 1 instead\n')
            stats_f2bad+= 1
        elif not sect1_done and not sect2_done and sect1 != sect2:
            badsect(i, "diff sector")
            sys.stdout.write('no resolve strategy\n')
            print(f'{sect1}\n\n{sect2}')
            raise AssertionError
    if sect1_done:
        fo.write(sect2)
    elif sect1_done and sect2_done:
        break
    else:
        fo.write(sect1)
    i+=1
    if i % mb == 0:
        statusline(i)
statusline(i)
print("\n\nsector stats:")
print(f"File1 bad: {stats_f1bad}")
print(f"File2 bad: {stats_f2bad}")
print(f"both  bad: {stats_fbbad}")
print(f"fixed    : {stats_fixed}")
fo.close()
f1.close()
f2.close()

print(f'{colors.NORMAL}\ndone.\n')