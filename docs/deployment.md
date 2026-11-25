# Deployment

For a personal workstation, use the [local setup](../README.md). A hosted instance sends uploaded material to its host to render the catalog. Use a private host with access controls for internal product data and use the included fictional samples on publicly accessible demos.

## Docker

```sh
docker build -t trade-catalog-kit .
docker run --rm -p 127.0.0.1:8501:8501 trade-catalog-kit
```

Open `http://127.0.0.1:8501`. The image runs as a non-root user and includes the Streamlit health endpoint. To build behind a managed TLS proxy, pass your organization's trusted CA bundle with `docker build --secret id=pip_cert,src=/path/to/ca-bundle.pem -t trade-catalog-kit .`. BuildKit provides the bundle during dependency installation.

## Streamlit Community Cloud

In your own Streamlit Community Cloud account, authorize its GitHub access, choose the project repository and its default branch, set the entrypoint to `app.py` and choose Python 3.12 in Advanced settings. `requirements.txt` installs the project with its web extra and `.streamlit/config.toml` supplies the theme and upload limit. The optional AI extra is excluded from this standard deployment.

[Official Streamlit deployment guide](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)
