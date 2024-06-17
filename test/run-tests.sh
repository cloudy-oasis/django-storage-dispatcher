#!/usr/bin/sh

set -eu

django_versions="2.2 3.2 4.2 5.0 5.1a1"
package_name='storage-dispatcher-0.1.tar.gz'
package_path='../dist'

test_path='../..'

for version in $django_versions; do
	printf "Django %s: " "$version"
	if [ -d "./django-$version" ]; then
		rm -r "./django-$version"
	fi

	# create and enter virtual environment
	printf "Building... "
	python3 -m venv "django-$version"
	ln -f "$package_path/$package_name" "django-$version/$package_name"
	cd "django-$version"
	. bin/activate

	# install dependencies
	pip install -q "django==$version" "$package_name"

	# set up django project
	django-admin startproject 'storagetest'
	cd storagetest
	cp -L "$test_path/tests-django-$version.py" "storagetest/test.py"

	# run tests
	echo "Running... "
	python manage.py test
	new_code="$?"
	return_code="$(( return_code > new_code ? return_code : new_code))"
	cd ..

	# exit and destroy virtual environment
	deactivate
	cd ..
	rm -r "django-$version"
done

echo "Tests returned $return_code"
exit "$return_code"

