import json
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import click
import pymysql
import requests
from bs4 import BeautifulSoup
from unidecode import unidecode


def get_final_url(url):
    # Parse the URL into components
    parsed_url = urlparse(url)
    # Extract the query component
    query_string = parsed_url.query
    # Parse the query string into a dictionary
    params = parse_qs(query_string)

    # Convert the list values to single values (if you want)
    url_params = {k: v[0] if len(v) == 1 else v for k, v in params.items()}

    # Strip existing query parameters and build a new query string with out the sid
    new_params = {
        "t": url_params["t"],
    }
    if "f" in url_params:
        new_params["f"] = url_params["f"],

    # Create the new query string
    new_query = urlencode(new_params)

    # Rebuild the URL with the new query string
    new_url = urlunparse(
        (
            parsed_url.scheme,
            parsed_url.netloc,
            parsed_url.path,
            parsed_url.params,
            new_query,  # Replacing the query part
            parsed_url.fragment,
        )
    )
    return int(url_params["t"]), new_url


def ignore_topic(class_list):
    """Checks if we should ignore this topic"""
    for item in class_list:
        # Global thread, ignore it
        if item.find("global_") != -1:
            return True
        # Locked, user dropped out, or it's an admin thread
        if item.find("read_locked") != -1:
            return True
    return False


@click.group()
def cli():
    pass


@cli.command()
@click.argument("url", default="https://forums.tgstation13.org/viewforum.php?f=38")
def candidates(url):
    """Fetches candidate threads and sets up the url for them and dumps to json for input into the make poll command"""
    # Base forum url.
    base = "https://forums.tgstation13.org"

    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        click.echo(f"Error fetching the page: {e}")
        return

    soup = BeautifulSoup(response.text, "html.parser")
    dl_elements = soup.find_all("dl", class_="row-item")
    filtered_elements = [dl for dl in dl_elements if not ignore_topic(dl.get("class"))]
    final = {}
    if filtered_elements:
        for idx, dl in enumerate(filtered_elements, start=1):
            topic_title = dl.find("a", class_="topictitle")
            if topic_title:
                text = unidecode(topic_title.get_text(strip=True))
                href = topic_title.get("href", "No href attribute")
                url = href.replace(".", base, 1)
                thread_id, url = get_final_url(url)
                # build the output dictionary, we want to sort by thread id, so use that as the key at first
                final[thread_id] = (text, url)

            else:
                pass
                # click.echo("  - No <a> element with class 'topic-title' found.")
    else:
        click.echo("No <dl> elements with class 'row-item' found.")

    # Sort by threads thread order with oldest thread first
    sorted_dict = dict(sorted(final.items()))
    true_final = dict()
    for key, (text, url) in sorted_dict.items():
        click.echo(f"{text} - {url}")
        true_final[text] = url
    with open("votes.json", "w") as json_file:
        json.dump(true_final, json_file, indent=4)


def create_poll_question(cursor, subtitle):
    sql = f"""
                INSERT INTO poll_question (
                    polltype,
                    created_datetime,
                    starttime,
                    endtime,
                    question,
                    subtitle,
                    adminonly,
                    multiplechoiceoptions,
                    createdby_ckey,
                    createdby_ip,
                    for_trialmin,
                    dontshow,
                    allow_revoting,
                    deleted
                )
                VALUES (
                    "IRV",
                    NOW(),
                    NOW(),
                    NOW() + INTERVAL 7 DAY,
                    "Headmin Election poll",
                    %s,
                    0,
                    NULL,
                    "optimumtact",
                    INET_ATON('127.0.0.1'),
                    NULL,
                    1,
                    1,
                    0
                )
                """
    cursor.execute(sql, subtitle)
    poll_id = cursor.lastrowid
    return poll_id


def add_poll_option(cursor, poll_id, text):
    qsql = f"""
                INSERT INTO poll_option (
                    pollid,
                    text,
                    default_percentage_calc,
                    deleted
                )
                VALUES (
                    {poll_id},
                    %s,
                    1,
                    0
                )
                """
    cursor.execute(qsql, text)
    click.echo(f"Inserted vote question {cursor.lastrowid}")


@cli.command()
@click.option("--host", prompt="Host", help="The mariadb/mysql host address")
@click.option("--user", prompt="User", help="The mariadb/mysql user name")
@click.option("--password", prompt="Password", help="The mariadb/mysql user password")
@click.option("--database", prompt="Database", help="The mariadb/mysql database")
def createthreatpoll(host, user, password, database):
    """Create the threat poll as required"""

    """Prompt the user to continue with a y/n response."""
    response = click.prompt("Do you want to continue? (y/n)", type=str, default="n")
    if response.lower() not in ("y", "yes"):
        click.echo("Not continuing")
        return

    click.echo(f"Creating your dumb poll")
    connection = pymysql.connect(
        host=host, user=user, password=password, database=database
    )
    threat_levels = [
        "Green Star - Greenshift",
        "Blue Star - 0-19 threat",
        "Yellow Star - 20-39 threat",
        "Orange Star - 40-65 threat",
        "Red Star - 66-79 threat",
        "Black Orbit - 80-99 threat",
        "Midnight Sun - 100 threat",
        "Pulsar Orbit - Unknown threat",
    ]

    with connection:
        with connection.cursor() as cursor:
            poll_id = create_poll_question(
                cursor,
                "Please rank the different round threat levels in the order you prefer, with most preferred at the top",
            )
            click.echo(f"Poll id was set: {poll_id}")
            for text in threat_levels:
                add_poll_option(cursor, poll_id, text)
                click.echo(f"Inserted {text}")
            connection.commit()


@cli.command()
@click.option("--host", prompt="Host", help="The mariadb/mysql host address")
@click.option("--user", prompt="User", help="The mariadb/mysql user name")
@click.option("--password", prompt="Password", help="The mariadb/mysql user password")
@click.option("--database", prompt="Database", help="The mariadb/mysql database")
def createpoll(host, user, password, database):
    """Create the poll as required"""

    # Path to the JSON file
    file_path = "votes.json"

    # Load the JSON file
    with open(file_path, "r") as file:
        votes = json.load(file)

        for index, (title, thread) in enumerate(votes.items()):
            click.echo(f"Will add option {index}: {title} - {thread}")
        """Prompt the user to continue with a y/n response."""
        response = click.prompt("Do you want to continue? (y/n)", type=str, default="n")
        if response.lower() not in ("y", "yes"):
            click.echo("Not continuing")
            return

        click.echo(f"Creating your dumb poll")
        connection = pymysql.connect(
            host=host, user=user, password=password, database=database
        )
        with connection:
            with connection.cursor() as cursor:
                sql = f"""
                    INSERT INTO poll_question (
                        polltype,
                        created_datetime,
                        starttime,
                        endtime,
                        question,
                        subtitle,
                        adminonly,
                        multiplechoiceoptions,
                        createdby_ckey,
                        createdby_ip,
                        for_trialmin,
                        dontshow,
                        allow_revoting,
                        deleted
                    )
                    VALUES (
                        "IRV",
                        NOW(),
                        NOW(),
                        NOW() + INTERVAL 7 DAY,
                        "Headmin Election poll",
                        %s,
                        0,
                        NULL,
                        "optimumtact",
                        INET_ATON('127.0.0.1'),
                        NULL,
                        1,
                        1,
                        0
                    )
                    """
                subtitle = 'Please rank the candidates in order you would like to see them as headadmins <a target="_blank" href="https://tgstation13.org/phpBB/viewtopic.php?f=38&t=9965">You can find more instructions on voting here.</a>'
                click.echo(sql)
                cursor.execute(sql, subtitle)
                poll_id = cursor.lastrowid
                click.echo(f"Poll id was set: {poll_id}")
                for title, thread in votes.items():
                    click.echo("Inserting vote")
                    qsql = f"""
                    INSERT INTO poll_option (
                        pollid,
                        text,
                        default_percentage_calc,
                        deleted
                    )
                    VALUES (
                        {poll_id},
                        %s,
                        1,
                        0
                    )
                    """
                    vote_text = f'<a target="_blank" href="{thread}">{title}</a>'
                    cursor.execute(qsql, vote_text)
                    click.echo(f"Inserted vote question {cursor.lastrowid}")
                connection.commit()


if __name__ == "__main__":
    cli()
