from datetime import datetime, timedelta
import os
import subprocess
import sys
from alphabet import ALPHABET


def calculate_message_width(message):
    """Calculate the total width needed for the message in columns"""
    width = 0
    for letter in message:
        if letter in ALPHABET:
            width += len(ALPHABET[letter][0]) + 1  # letter width + spacing
    return width - 1  # subtract the last spacing


def word_to_matrix(message):
    """
    Convert a word into a 7x52 contribution graph matrix.
    Returns a 2D array representing the contribution pattern.
    """
    # Convert message to uppercase
    message = message.upper()

    # Create a 7x52 matrix (full week x 52 weeks) initialized with empty squares
    matrix = [[0] * 52 for _ in range(7)]

    # Calculate center offset
    message_width = calculate_message_width(message)
    offset = (52 - message_width) // 2  # Center horizontally

    # Fill in the matrix based on the message
    for letter in message:
        if letter in ALPHABET:
            pattern = ALPHABET[letter]
            # Copy the pattern to the matrix at the current offset
            for row in range(5):  # 5 rows (Tuesday-Saturday)
                for col in range(len(pattern[0])):  # 5 columns per letter
                    if offset + col < 52:  # Ensure we don't exceed matrix width
                        matrix[row + 1][offset + col] = pattern[row][
                            col
                        ]  # +1 to skip Sunday row
            offset += (
                len(pattern[0]) + 1
            )  # Move offset to next position (add 1 for spacing)

    return matrix


def visualize_matrix(matrix):
    """
    Visualize a 2D matrix as a contribution graph.
    Uses '⬛' for filled squares and '⬜' for empty squares.
    """
    for row in range(7):
        for col in range(52):
            print("⬛" if matrix[row][col] else "⬜", end="")
        print()  # New line after each row


def matrix_to_dates(matrix, start_date):
    """
    Convert a 2D matrix into a list of dates that need contributions.
    start_date should be a Sunday (weekday 6).
    """
    dates = []
    for row in range(7):
        for col in range(52):
            if matrix[row][col] == 1:
                # Calculate the date:
                # Move forward by column * 7 for weeks
                # Add row days to get the specific day of the week
                current_date = start_date + timedelta(days=col * 7 + row)
                dates.append(current_date)
    return dates


def create_git_contributions(dates):
    """
    Create git commits for each date in the dates list.
    Creates an orphan branch named 'gh-pages' and adds commits at 12PM UTC for each date.

    Raises:
        RuntimeError: If repository has uncommitted changes or if author/committer details cannot be retrieved
    """
    # Check for uncommitted changes
    status = subprocess.run(
        ["git", "status", "--porcelain"], capture_output=True, text=True
    ).stdout.strip()

    if status:
        raise RuntimeError(
            "Repository has uncommitted changes. Please commit or stash them first."
        )

    # Get author and committer details from the first commit
    first_commit = (
        subprocess.run(
            ["git", "log", "--reverse", "--format=%an%n%ae%n%cn%n%ce", "-1"],
            capture_output=True,
            text=True,
        )
        .stdout.strip()
        .split("\n")
    )

    if len(first_commit) != 4:
        raise RuntimeError("Could not get author and committer details from repository")

    author_name, author_email, committer_name, committer_email = first_commit

    # Delete existing gh-pages branch if it exists
    subprocess.run(
        ["git", "branch", "-D", "gh-pages"],
        stderr=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
    )

    # Create new orphan branch
    subprocess.run(
        ["git", "checkout", "--orphan", "gh-pages"],
        stderr=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
    )

    # Remove everything from the working directory and staging area
    subprocess.run(
        ["git", "rm", "-rf", "."], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL
    )

    # Create a commit for each date
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = author_name
    env["GIT_AUTHOR_EMAIL"] = author_email
    env["GIT_COMMITTER_NAME"] = committer_name
    env["GIT_COMMITTER_EMAIL"] = committer_email

    for date in dates:
        # Set commit date to 12PM UTC
        commit_date = date.replace(hour=12, minute=0, second=0, microsecond=0)
        date_str = commit_date.strftime("%Y-%m-%d 12:00:00 +0000")

        # Set environment variables for commit dates
        env["GIT_AUTHOR_DATE"] = date_str
        env["GIT_COMMITTER_DATE"] = date_str

        # Create empty commit
        subprocess.run(
            [
                "git",
                "commit",
                "--allow-empty",
                "-m",
                f"Contribution for {date.strftime('%Y-%m-%d')}",
            ],
            env=env,
        )


def main(message):
    # get the current date
    today = datetime.now()
    one_year_ago = today - timedelta(days=365)

    # Find the first Sunday before or on one_year_ago
    while one_year_ago.weekday() != 6:  # 6 is Sunday
        one_year_ago -= timedelta(days=1)

    # Generate matrix
    matrix = word_to_matrix(message)

    # Print preview
    visualize_matrix(matrix)

    # Generate dates
    dates = matrix_to_dates(matrix, one_year_ago)

    # Create git contributions
    create_git_contributions(dates)

    return dates


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py MESSAGE")
        sys.exit(1)
    main(message=" ".join(sys.argv[1:]))
