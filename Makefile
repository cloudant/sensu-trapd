DESTDIR=/
PROJECT=sensu-snmp
VERSION :=$(shell bash version.sh )
RELEASE :=$(shell ls -1 dist/*.noarch.rpm 2>/dev/null | wc -l )
HASH	:=$(shell git rev-parse HEAD )

all:
	@echo "make test     - Run tests"
	@echo "make sdist    - Create source package"
	@echo "make bdist    - Create binary package"
	@echo "make install  - Install on local system"
	@echo "make rpm      - Generate a rpm package"
	@echo "make deb      - Generate a deb package"
	@echo "make tar      - Generate a tar ball"
	@echo "make clean    - Get rid of scratch and byte files"

test:
	./test.py

sdist: version
	./setup.py sdist --prune

bdist: version
	./setup.py bdist --prune

install: version
	./setup.py install --root $(DESTDIR)

rpm: buildrpm

buildrpm: sdist
	./setup.py bdist_rpm \
		--post-install=rpm/postinstall \
		--pre-uninstall=rpm/preuninstall \
		--install-script=rpm/install \
		--release=`ls dist/*.noarch.rpm | wc -l`

deb: builddeb

builddeb: version 
	dch --newversion $(VERSION) --distribution unstable --force-distribution -b "Last Commit: $(shell git log -1 --pretty=format:'(%ai) %H %cn <%ce>')"
	dch --release  "new upstream"
	./setup.py sdist --prune
	mkdir -p build
	tar -C build -zxf dist/$(PROJECT)-$(VERSION).tar.gz
	(cd build/$(PROJECT)-$(VERSION) && debuild -us -uc -v$(VERSION))
	@echo "Package is at build/$(PROJECT)_$(VERSION)_all.deb"

tar: sdist

clean:
	./setup.py clean
	rm -rf dist build MANIFEST .tox *.log
	find . -name '*.pyc' -delete

version:
	./version.sh > version.txt

vertest: version 
	echo "${VERSION}"

reltest:
	echo "$(RELEASE)"

.PHONY: test sdist bdist install rpm buildrpm deb builddeb tar clean version reltest vertest
