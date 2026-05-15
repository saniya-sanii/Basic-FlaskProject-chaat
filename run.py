## Pruthviraj Mundargi pm935@drexel.edu
## Saivinay Rayala sr3674@drexel.edu
## CS530: DUI


# run.py

from app import create_app

app = create_app()
app.secret_key = "restaurant123"

if __name__ == '__main__':
    print("log:hello app started")
    app.run(host="0.0.0.0", port=8080, debug=True)

