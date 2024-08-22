import json
from urllib.parse import parse_qs, urlparse

import click
import pymysql
import requests
from bs4 import BeautifulSoup
from unidecode import unidecode


def get_query_params(url):
    # Parse the URL
    parsed_url = urlparse(url)

    # Extract the query component
    query_string = parsed_url.query

    # Parse the query string into a dictionary
    params = parse_qs(query_string)

    # Convert the list values to single values (if you want)
    params_dict = {k: v[0] if len(v) == 1 else v for k, v in params.items()}

    return params_dict


@click.group()
def cli():
    pass


@cli.command()
@click.argument("url", default="https://tgstation13.org/phpBB/viewforum.php?f=38")
def candidates(url):
    """Fetches candidate threads and sets up the url for them and dumps to json for input into the make poll command"""
    # Base forum url.
    base = "https://tgstation13.org/phpBB"
    blacklisted_thread_ids = [
        "36731",
        "3371",
        "336",
        "28546",
        "9965",
        "21851",
        "15742",
        "12685",
        "12617",
    ]

    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        click.echo(f"Error fetching the page: {e}")
        return

    soup = BeautifulSoup(response.text, "html.parser")
    dl_elements = soup.find_all("dl", class_="row-item")
    filtered_elements = [
        dl for dl in dl_elements if not "topic_read_locked" in dl.get("class")
    ]
    final = {}
    if filtered_elements:
        for idx, dl in enumerate(filtered_elements, start=1):
            topic_title = dl.find("a", class_="topictitle")
            if topic_title:
                text = unidecode(topic_title.get_text(strip=True))
                href = topic_title.get("href", "No href attribute")
                url = href.replace(".", base, 1)
                params = get_query_params(url)
                if params["t"] in blacklisted_thread_ids:
                    click.echo(f"Ignoring thread {text} - {url}")
                    continue
                click.echo(f"  - Title: {text}")
                click.echo(f"  - URL: {url}")
                # build the output dictionary
                final[text] = href.replace(".", base, 1)
            else:
                click.echo("  - No <a> element with class 'topic-title' found.")
    else:
        click.echo("No <dl> elements with class 'row-item' found.")
    with open("votes.json", "w") as json_file:
        json.dump(final, json_file, indent=4)


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
                cursor.execute(sql, subtitle)
                poll_id = cursor.lastrowid
                click.echo(f"Poll id was set: {poll_id}")
                for vote in votes:
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
                    vote_text = f'<a target="_blank" href="{vote[1]}">{vote[0]}</a>'
                    cursor.execute(qsql, vote_text)
                    click.echo(f"Inserted vote question {cursor.lastrowid}")
                connection.commit()


if __name__ == "__main__":
    cli()
