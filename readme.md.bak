#Installation
##New directory lib
mkdir /mnt/project/lib
python3 -m venv myenv

##Install clingo version 
python3 -m venv clingoenv
source clingoenv/bin/activate
pip install clinguin

##Install command line version of clingo
sudo apt install gringo

##Install fasb
sudo apt install curl build-essential
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env

sudo apt install cmake

git clone https://github.com/drwadu/fasb.git
mv fasb fasb_normal
git clone https://github.com/drwadu/fasb.git
mv fasb fasb_interp
cd fasb_normal 
cargo build -r
cd ..
cd fasb_interp
cargo build -r --features interpreter


##Export path for normal
export PATH="/mnt/project/lib/fasb_normal/target/release:$PATH"

##Export path for fasb_interp
export PATH="/mnt/project/lib/fasb_interp/target/release:$PATH"

cd /mnt/project
git init
nano .gitignore
##following content in gitignore
## Ignore lib folder
lib/
## Ignore IDE/editor files
.vscode/
.idea/
*.swp
*.swo

##Download epas
git clone https://github.com/choupara/thesis_epasufr.git
cd thesis_epasufr/src


# Quickstart

##epas: find out facet count of projected away answer sets.
```
$ python epas.py example.lp
Choose the type of limit you want to set:
1. Limit by number of answer sets
2. Limit by time (seconds)
3. No limits (run to completion)
Enter your choice (1, 2, or 3): 3
Main started: 2025-11-28 14:17:45.843718
Do you want to enable navigation mode? (y/n): n
```
##epas: Naviagting one answer set
```
$ python epas.py example.lp
Choose the type of limit you want to set:
1. Limit by number of answer sets
2. Limit by time (seconds)
3. No limits (run to completion)
Enter your choice (1, 2, or 3): 3
Main started: 2025-11-28 14:17:45.843718
Do you want to enable navigation mode? (y/n): y
✅Answer Set 1: [order_dish(salad), order_drink(juice), total_cost(12), cost_category(moderate)]

Answer Set with ONLY projected atom: [ cost_category(moderate) ]
Facet Count:  8

✅Answer Set 2: [order_dish(salad), order_drink(water), total_cost(9), cost_category(budget)]

Answer Set with ONLY projected atom: [ cost_category(budget) ]
Facet Count:  4

✅Answer Set 3: [order_dish(pizza), order_drink(water), total_cost(16), cost_category(premium)]

Answer Set with ONLY projected atom: [ cost_category(premium) ]
Facet Count:  8
Warning: No start time recorded for key 'Clingo time(Projection + Facet Count algorithm)'

Total answer sets found: 3

 Navigation Mode Activated

Available Answer Set Options:

1: [order_dish(salad), order_drink(juice), total_cost(12), cost_category(moderate)]
2: [order_dish(salad), order_drink(water), total_cost(9), cost_category(budget)]
3: [order_dish(pizza), order_drink(water), total_cost(16), cost_category(premium)]

Select Answer Set Index for Navigation [1, ..., 3]: 1     -- user input answer set
Bag of loop navigation atom []

Navigation round: 1

 1: Deactivate previous facet
 2: Deactivate all facets
 3: Activate new facet
 4: Diversity measure under each facet
 5: Quit navigation
 Enter command (1/2/3/4/5):                         -- user input navigation action
```
