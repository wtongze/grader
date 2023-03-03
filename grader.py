#!/usr/bin/env python3

import os
import sys
import subprocess
import re
import json
import argparse
from datetime import datetime


class Commit:
  hash: str
  authorName: str
  authorEmail: str
  date: datetime
  files: int
  insertions: int
  deletions: int

  def __init__(self, hash, authorName, authorEmail, date, files, insertions, deletions):
    self.hash = hash
    self.authorName = authorName
    self.authorEmail = authorEmail
    self.date = date
    self.files = files
    self.insertions = insertions
    self.deletions = deletions

  def __str__(self) -> str:
    return f"{self.hash}: {self.authorName} <{self.authorEmail}> @ {self.date}: {self.files} +{self.insertions} -{self.deletions}"


def execute(cmd: str):
  process = subprocess.run(cmd, shell=True, capture_output=True)
  if (process.returncode != 0):
    raise Exception(process.stderr.decode())
  return process.stdout.decode()


def main():
  parser = argparse.ArgumentParser(
      prog='grader.py',
      description='Count the commits inside git repositories for grading',
      epilog='Source: https://github.com/wtongze/grader')

  parser.add_argument('path', metavar="PATH", type=str, nargs='+',
                      help='Paths of git repos')
  parser.add_argument('-m', '--mapping', type=str, nargs='?',
                      help='Path of mapping file')

  args = parser.parse_args()
  # print(args)

  mapping = {}
  dirs = args.path
  try:
    if args.mapping is not None:
      f = open(args.mapping)
      mapping = json.load(f)
      f.close()
  except:
    raise Exception("Couldn't read mapping file")

  currPath = os.getcwd()

  commits: list[Commit] = []
  authorSet = set()

  for dir in dirs:
    print(f"Working on {dir}")

    # Change working directory
    os.chdir(dir)

    # Check if it's a git repository
    execute("git rev-parse --is-inside-work-tree")

    commitHashes = (
        execute('git --no-pager log --pretty="format:%H"')).split('\n')

    for commitHash in commitHashes:
      raw = execute(f'git show --stat "{commitHash}"')

      rawMerge = re.search("Merge:\s.{7}\s.{7}", raw)
      if rawMerge:
        continue

      # File, Insertion, Deletion
      delta = [0, 0, 0]
      name = ""
      email = ""
      date = datetime.now()

      rawAuthor = re.search("Author:\s(.+)\s<(.+)>\n", raw)
      if rawAuthor:
        name = rawAuthor.groups()[0]
        email = rawAuthor.groups()[1]
      else:
        raise Exception(f"{commitHash}: Can't find author info")

      rawDate = re.search("Date:\s+(.+)\n", raw)
      if rawDate:
        date = datetime.strptime(
            rawDate.groups()[0], "%a %b %d %H:%M:%S %Y %z")
      else:
        raise Exception(f"{commitHash}: Can't find date")

      rawFile = re.search("\n\s(\d)+\sfiles?\schanged,", raw)
      if rawFile:
        delta[0] = int(rawFile.groups()[0])

      rawInsert = re.search("(\d+)\sinsertions?\(\+\)", raw)
      if rawInsert:
        delta[1] = int(rawInsert.groups()[0])

      rawDeletion = re.search("(\d+)\sdeletions?\(\-\)", raw)
      if rawDeletion:
        delta[2] = int(rawDeletion.groups()[0])

      commit = Commit(commitHash, name, email, date, *delta)
      commits.append(commit)
      authorSet.add((name, email))
    os.chdir(currPath)

  print()
  if (len(mapping) == 0):
    print("Authors")
    print("-" * 40)
    for name, email in authorSet:
      print(name.ljust(20), email)
    print()

  commitDictByEmail = {}
  for commit in commits:
    k = commit.authorEmail
    if (len(mapping) > 0):
      for name, emails in mapping.items():
        if commit.authorEmail in emails:
          k = name
          break
    if not k in commitDictByEmail:
      commitDictByEmail[k] = []
    commitDictByEmail[k].append(commit)

  # Print total stats
  emailMaxSize = len(max(commitDictByEmail.keys(), key=len))
  seperator = " " * 3
  cols = [("Email", emailMaxSize), ("Commits", 7), ("Files", 5),
          ("Inserts", 7), ("Deletes", 7), ("Total", 7)]
  for idx, (name, width) in enumerate(cols):
    if (idx == 0):
      print(name.ljust(width), end=seperator)
    else:
      print(name.rjust(width), end=seperator)
  print()
  for name, width in cols:
    print("-" * width, end=seperator)
  print()

  for k, v in commitDictByEmail.items():
    # Files, Inserts, Deletes
    total = [0, 0, 0]
    for c in v:
      total[0] += c.files
      total[1] += c.insertions
      total[2] += c.deletions
    content = [k, len(v), *total, total[1] + total[2]]
    for idx, e in enumerate(cols):
      if (idx == 0):
        print(str(content[idx]).ljust(e[1]), end=seperator)
      else:
        print(str(content[idx]).rjust(e[1]), end=seperator)
    print()


main()
