This project makes headmin polls easy
## Installation
Install poetry https://python-poetry.org/docs/#installation

    cd makepoll
    poetry init
    poetry run python makepoll/script.py create-poll


## Docker
    docker build --tag makepoll .
    docker run -it makepoll