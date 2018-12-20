#!/usr/bin/env python3

import argparse
import functools
import json
from pathlib import Path
import typing

from make_github_issue import GitHub, GitHubIdentity
from parse_actions import  REPO_NAME, REPO_OWNER
from parse_actions import Action, process_actions_returning_lines


class ActionsProcessor:
    def __init__(
        self,
        api: GitHub,
        name_map: typing.Dict[str, GitHubIdentity],
        dry_run: bool,
    ) -> None:
        self.api = api
        self.name_map = name_map
        self.dry_run = dry_run

    def _process_action(
        self,
        action: Action,
        from_url: str,
    ) -> typing.Optional[int]:
        if action.id is not None:
            # Leave existing entries alone
            return action.id

        try:
            assignee = self.name_map[action.owner]
        except KeyError:
            print(
                "Unknown assignee {!r}. Either adjust the action or add them to"
                " the name map file",
            )
            return None

        body = "From {}".format(from_url)
        body_for_print = "\n> " + ("\n> ".join(body.splitlines()))

        if self.dry_run:
            print("Would create issue for @{} to {!r} with body:{}".format(
                assignee,
                action.title,
                body_for_print,
            ))
            return None

        print("Creating issue for @{} to {!r} with body:{}".format(
            assignee,
            action.title,
            body_for_print,
        ))

        issue = self.api.make_issue(action.title, body, assignee)

        print("Created issue {} assigned to @{}: {}".format(
            issue.id,
            ", @".join(issue.assignees),
            issue.title,
        ))

        return issue.id

    def process_actions(self, markdown_file: typing.TextIO) -> None:
        print("Processing {}...".format(markdown_file.name))
        from_url = 'https://github.com/{}/{}/blob/master/{}#specific'.format(
            REPO_OWNER,
            REPO_NAME,
            markdown_file.name,
        )

        markdown_file.seek(0)
        lines = process_actions_returning_lines(
            markdown_file.read(),
            functools.partial(self._process_action, from_url=from_url),
        )

        if not self.dry_run:
            markdown_file.seek(0)
            markdown_file.write("\n".join(lines))


def load_name_map() -> typing.Dict[str, GitHubIdentity]:
    name_map_file = Path(__file__).parent.parent / '.name_map.json'
    logins_to_names = json.loads(name_map_file.read_text())
    return {
        name: GitHubIdentity(login)
        for login, names in logins_to_names.items()
        for name in names
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--dry-run',
        default=False,
        action='store_true',
    )
    parser.add_argument(
        'actions_files',
        metavar='MINUTES.md',
        nargs='+',
        type=argparse.FileType(mode='r+'),
    )
    return parser.parse_args()


def main(args):
    name_map = load_name_map()

    processor = ActionsProcessor(
        GitHub(REPO_OWNER, REPO_NAME),
        name_map,
        args.dry_run,
    )

    for markdown_file in args.actions_files:
        processor.process_actions(markdown_file)


if __name__ == '__main__':
    main(parse_args())
