
.PHONY: all clean installdeps

all:
	python -m sphinx . html

clean:
	rm -rf html

installdeps:
	python -m pip install --upgrade --upgrade-strategy=eager -r requirements.txt
