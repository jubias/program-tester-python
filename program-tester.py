#!/usr/bin/env python3
import argparse
import sys
import os
import tempfile
import subprocess
import timeit
import textwrap

__version__ = '0.3'


class Colors(object):
	green = "\033[1m\033[92m"
	yellow = "\033[1m\033[93m"
	red = "\033[1m\033[91m"
	reset = "\033[1m\033[0m"
	ok = green
	completed = yellow
	wrong = red
	error = red

	@classmethod
	def turn_off(cls):
		cls.green = ""
		cls.yellow = ""
		cls.red = ""
		cls.reset = ""
		cls.ok = ""
		cls.completed = ""
		cls.wrong = ""
		cls.error = ""


class Options(object):
	program = ''
	tests_folder = ''
	tests_list = []
	force_colors = 0
	show_time = 1
	show_comparision = 1
	show_summary = 1
	show_test_ok = 1
	show_test_wrong = 1
	show_test_completed = 1
	show_test_error = 1


class Results(object):
	def __init__(self):
		self.tests_ok = 0
		self.tests_wrong = 0
		self.tests_completed = 0
		self.tests_error = 0

	def add_ok(self):
		self.tests_ok += 1

	def add_wrong(self):
		self.tests_wrong += 1

	def add_completed(self):
		self.tests_completed += 1

	def add_error(self):
		self.tests_error += 1

	def get_ok(self):
		return self.tests_ok

	def get_wrong(self):
		return self.tests_wrong

	def get_completed(self):
		return self.tests_completed

	def get_error(self):
		return self.tests_error


# See: http://stackoverflow.com/a/32974697
class MultilineFormatter(argparse.HelpFormatter):
	def _fill_text(self, text, width, indent):
		text = self._whitespace_matcher.sub(' ', text).strip()
		paragraphs = text.split('|n ')
		multiline_text = ''

		for paragraph in paragraphs:
			formatted_paragraph = textwrap.fill(paragraph, width, initial_indent=indent, subsequent_indent=indent) + '\n'
			multiline_text = multiline_text + formatted_paragraph

		return multiline_text


def check_terminal():
	if not Options.force_colors:
		if not sys.stdout.isatty():
			Colors.turn_off()


def read_arguments():
	parser = argparse.ArgumentParser(__file__, formatter_class=MultilineFormatter,
									 description="Tester programow. Skrypt uruchamia program na serii testow, przekierowuje wejscie programu i sprawdza czy wyjscie programu jest takie samo jak wyjscie testu. Mozliwe odpowiedzi to: OK, SKONCZONE, ZLE, BLAD WYKONANIA.|n |n OK - program zakonczyl sie i odpowiedz sie zgadza |n SKONCZONE - program zakonczyl sie, ale nie ma z czym porownac odpowiedzi |n ZLE - program zakonczyl sie, ale dal inna odpowiedz |n BLAD WYKONANIA - program zwrocil kod wyjscia rozny od zera")

	parser.add_argument("PROGRAM", type=str, help="sciezka do programu wykonywalnego")

	parser.add_argument("TESTY", type=str, help="sciezka do folderu z testami (zawiera pliki *.in oraz *.out)")

	parser.add_argument("--test", type=str, action='append', help="nazwa testu bez sufiksu .in; program jest testowany na konkretnym tescie; parametr moze wystapic wiecej niz raz")

	parser.add_argument("--portable", action="store_true", help="alias dla -TC")

	parser.add_argument("--quiet", action="store_true", help="alias dla -O")

	parser.add_argument("-T", "--no-time", action="store_true", help="nie wyswietlaj czasu dzialania programu")

	parser.add_argument("-C", "--no-compare", action="store_true", help="nie wyswietlaj porownania odpowiedzi blednej i poprawnej")

	parser.add_argument("-O", "--no-ok", action="store_true", help="nie wyswietlaj testow, ktore program przeszedl poprawnie")

	parser.add_argument("-E", "--no-error", action="store_true", help="nie wyswietlaj testow, ktorych program nie przeszedl poprawnie")

	color = parser.add_mutually_exclusive_group()

	color.add_argument("--color", action="store_true", help="wymus wlaczenie kolorow")

	color.add_argument("--no-color", action="store_true", help="wymus wylaczenie kolorow")

	parser.add_argument("--no-summary", action="store_true", help="nie wyswietlaj podsumowania")

	parser.add_argument("-V", "--version", action="version", version=__version__)

	return parser.parse_args()


def parse_arguments(arg):
	Options.program = os.path.abspath(arg.PROGRAM)
	Options.tests_folder = os.path.abspath(arg.TESTY)

	if arg.test:
		Options.test_mode = 1
		for test in arg.test:
			Options.tests_list.append(test)

	if arg.portable:
		Options.show_time = 0
		Options.show_comparision = 0

	if arg.quiet:
		Options.show_test_ok = 0
		Options.show_test_completed = 0

	if arg.no_time:
		Options.show_time = 0

	if arg.no_compare:
		Options.show_comparision = 0

	if arg.no_ok:
		Options.show_test_ok = 0
		Options.show_test_completed = 0

	if arg.no_error:
		Options.show_test_error = 0
		Options.show_test_wrong = 0

	if arg.color:
		Options.force_colors = 1

	if arg.no_color:
		Colors.turn_off()

	if arg.no_summary:
		Options.show_summary = 0


def check_files():
	if not os.path.isfile(Options.program):
		print("Plik wykonywalny nie istnieje:\n" + Options.program + "\n")
		raise FileNotFoundError

	if not os.path.exists(Options.tests_folder):
		print("Folder z testami nie istnieje:\n" + Options.tests_folder + "\n")
		raise FileNotFoundError


def print_tests_summary(results):
	print("\n\n-----")

	print("Poprawne: " + Colors.ok + str(results.get_ok()) + Colors.reset)

	if results.get_completed() > 0:
		print("Skonczone: " + Colors.completed + str(results.get_completed()) + Colors.reset)

	print("Niepoprawne: " + Colors.wrong + str(results.get_wrong()) + Colors.reset)

	print("Bledy wykonania: " + Colors.error + str(results.get_error()) + Colors.reset)


def print_time(time):
	if Options.show_time:
		print("czas: {:.2f}\n".format(time))


def print_test_result(test_name, status, time=-1, comparison=''):
	separator = ":\t"

	# ok
	if status == 0:
		if Options.show_test_ok:
			print("Test " + test_name + separator + Colors.ok + "OK" + Colors.reset)
			print_time(time)
	# wrong
	elif status == 1:
		if Options.show_test_wrong:
			print("Test " + test_name + separator + Colors.wrong + "ZLE" + Colors.reset)
			if Options.show_comparision:
				print(comparison)
				print("(wynik programu | prawidlowy wynik)")
			print_time(time)
	# completed
	elif status == 2:
		if Options.show_test_completed:
			print("Test " + test_name + separator + Colors.completed + "SKONCZONY" + Colors.reset)
			print_time(time)
	# error
	elif status == 3:
		if Options.show_test_error:
			print("Test " + test_name + separator + Colors.error + "BLAD WYKONANIA" + Colors.reset)
			print_time(time)
	else:
		pass


def make_prefix(text, length):
	text_list = text.split('\n', 1)
	text = text_list[0]
	if len(text) <= length:
		if len(text_list) > 1:
			if len(text) <= length-3:
				return "%s..." % (text[:length])
			else:
				return "%s..." % (text[:length - 3])
		else:
			return text
	else:
		return "%s..." % (text[:length - 3])


def run_test(test_name, test_in, test_out, results):
	with open(test_in, 'rt') as file_in, tempfile.SpooledTemporaryFile(mode='r+t') as file_out:
		process = subprocess.Popen(Options.program, stdin=file_in, stdout=file_out, stderr=subprocess.DEVNULL, shell=False)
		process.wait()

		# TODO - run only once program
		# Maybe helps:
		# subprocess.run() -> https://docs.python.org/3/library/subprocess.html#subprocess.run
		if Options.show_time:
			try:
				start = timeit.default_timer()
				time = timeit.timeit(
					stmt="subprocess.check_call(PROGRAM, stdin=file_in, stdout=subprocess.DEVNULL,\
					stderr=subprocess.DEVNULL, shell=False)",
					setup="import subprocess; import os; PROGRAM='" + Options.program
						  + "'; file_in = open( '" + test_in + "' , 'r');",
					number=1
				)
			except:
				time = timeit.default_timer() - start
		else:
			time = 0
		# ##### #

		if process.returncode != 0:
			results.add_error()

			print_test_result(test_name, 3, time)
		else:
			try:
				with open(test_out, 'rt') as file_answer:
					file_out.seek(0)
					if file_answer.read().strip() == file_out.read().strip():
						results.add_ok()

						print_test_result(test_name, 0, time)
					else:
						results.add_wrong()

						file_answer.seek(0)
						file_out.seek(0)

						# Hardcoded numbers 100 and 25. Hmm...
						answer = file_answer.read(100).strip()
						out = file_out.read(100).strip()

						comparison = make_prefix(out.strip(), 25) + "  |  " + make_prefix(answer.strip(), 25)

						print_test_result(test_name, 1, time, comparison)
			except OSError:
				results.add_completed()

				print_test_result(test_name, 2, time)


def run_tests():
	results = Results()
	tests = {}

	if Options.tests_list:
		for file in os.listdir(Options.tests_folder):
			for name in Options.tests_list:
				if file.lower().endswith('.in') and name == os.path.splitext(file)[0]:
					file = os.path.join(Options.tests_folder, file)
					tests[name] = (file, '')

		for file in os.listdir(Options.tests_folder):
			for name in Options.tests_list:
				if file.lower().endswith('.out') and name == os.path.splitext(file)[0]:
					if name in tests:
						test = tests[name]
						file = os.path.join(Options.tests_folder, file)
						tests[name] = (test[0], file)
	else:
		for file in os.listdir(Options.tests_folder):
			if file.lower().endswith('.in'):
				name = os.path.splitext(file)[0]
				file_in = os.path.join(Options.tests_folder, file)
				tests[name] = (file_in, '')

		for file in os.listdir(Options.tests_folder):
			if file.lower().endswith('.out'):
				name = os.path.splitext(file)[0]
				if name in tests:
					test = tests[name]
					file_out = os.path.join(Options.tests_folder, file)
					tests[name] = (test[0], file_out)

	for (test_name, test_files) in sorted(tests.items()):
		run_test(test_name, test_files[0], test_files[1], results)

	if Options.show_summary:
		print_tests_summary(results)


def main():
	arguments = read_arguments()
	parse_arguments(arguments)
	check_terminal()
	check_files()
	run_tests()


if __name__ == "__main__":
	# Minimum python version:
	# 3.0
	# 3.2 - PEP 389, module argparse
	# 3.3 - PEP 3151, OSError and IOError means the same
	# 3.3 - subprocess, new constant DEVNULL
	minimum_version = (3, 3)
	if sys.version_info >= minimum_version:
		main()
	else:
		print("Wersja pythona:  "+str(sys.version_info[0])+"."+str(sys.version_info[1]))
		print("Wymagana wersja pythona:  >=" + str(minimum_version[0]) + "." + str(minimum_version[1]))

	raise SystemExit
