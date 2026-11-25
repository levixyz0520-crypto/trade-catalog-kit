# Deployment

For a personal workstation, use the [local setup](../README.md). A hosted instance sends uploaded material to its host to render the catalog. Use a private host with access controls for internal product data and use the included fictional samples on publicly accessible demos.

## Docker

```sh
docker build -t trade-catalog-kit .
docker run --rm -p 127.0.0.1:8501:8501 trade-catalog-kit
```

Open `http://127.0.0.1:8501`. The image runs as a non-root user and includes the Streamlit health endpoint. To build behind a managed TLS proxy, pass your organization's trusted CA bundle with `docker build --secret id=pip_cert,src=/path/to/ca-bundle.pem -t trade-catalog-kit .`. BuildKit provides the bundle during dependency installation.

## Streamlit Community Cloud

1. Sign in to [Streamlit Community Cloud](https://share.streamlit.io/) and connect the `levixyz0520-crypto` GitHub account. Authorization for public repositories is sufficient for this demo.
2. Choose **Create app**, then **Yup, I have an app**. Enter `levixyz0520-crypto/trade-catalog-kit` for the repository, `main` for the branch and `app.py` for the file path. You may choose a demo subdomain if one is available.
3. Under **Advanced settings**, select Python 3.12. Leave the secrets field empty. Click **Deploy**.
4. After deployment, check that the assigned `streamlit.app` URL opens in a signed-out browser session. Select **Try the included furniture example**, generate the PDF preview and confirm that the PDF downloads.

`requirements.txt` installs the project with its web extra. `.streamlit/config.toml` sets the theme and upload limit. The standard deployment serves the fictional furniture demo. The optional AI extra requires a separate install.

[Official GitHub connection guide](https://docs.streamlit.io/deploy/streamlit-community-cloud/get-started/connect-your-github-account) · [Official deployment guide](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)
