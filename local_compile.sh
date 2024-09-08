mkdir bin
mkdir bin/maoto_agent
cp -r src/maoto_agent/* bin/maoto_agent/
pyarmor gen -O bin/maoto_agent -r src/maoto_agent/maoto_agent.py
mkdir bin/pyarmor_runtime_000000
mv bin/maoto_agent/pyarmor_runtime_000000/* bin/pyarmor_runtime_000000

# pip uninstall maoto_agent -y

# pip install setuptools setuptools-scm cython wheel twine
# pip install graphqlclient==0.2.4 aiohttp==3.10.5 aiofiles==24.1.0 requests==2.32.3 openai==1.43.0 gql==3.5.0 websockets==13.0.1 numpy==2.1.1

# python setup.py clean --all
# python setup.py build_ext --build-lib build_output/lib
# python setup.py bdist_wheel --dist-dir build_output/dist

# pip install build_output/dist/maoto_agent-0.0.0-cp310-cp310-macosx_10_9_x86_64.whl
# python -c "import maoto_agent; maoto_agent.__main__.main()"