# Pilot summary — 559 instances, 0 errors/skips

| config | R@1 | R@5 | R@10 | Hit@5 | Hit@10 | MAP | n |
|---|---|---|---|---|---|---|---|
| bm25_a050_l90 | 0.307 | 0.560 | 0.623 | 0.590 | 0.648 | 0.432 | 559 |
| bm25_a075_l90 | 0.298 | 0.569 | 0.622 | 0.597 | 0.646 | 0.427 | 559 |
| bm25_a075_l30 | 0.300 | 0.565 | 0.622 | 0.594 | 0.646 | 0.429 | 559 |
| bm25_a025_l90 | 0.297 | 0.562 | 0.621 | 0.590 | 0.649 | 0.426 | 559 |
| bm25_a050_l30 | 0.308 | 0.561 | 0.621 | 0.592 | 0.648 | 0.432 | 559 |
| bm25_a050_l0 | 0.311 | 0.566 | 0.621 | 0.597 | 0.646 | 0.437 | 559 |
| bm25_a025_l30 | 0.296 | 0.566 | 0.621 | 0.596 | 0.648 | 0.426 | 559 |
| bm25_a025_l0 | 0.303 | 0.559 | 0.620 | 0.589 | 0.648 | 0.430 | 559 |
| bm25_a100_l0 | 0.284 | 0.561 | 0.620 | 0.590 | 0.644 | 0.415 | 559 |
| bm25_a075_l0 | 0.296 | 0.571 | 0.619 | 0.599 | 0.642 | 0.427 | 559 |
| bm25_a000_l0 | 0.295 | 0.544 | 0.616 | 0.572 | 0.644 | 0.423 | 559 |
| bm25_a000_l90 | 0.294 | 0.556 | 0.614 | 0.587 | 0.644 | 0.421 | 559 |
| bm25_a000_l30 | 0.285 | 0.561 | 0.614 | 0.592 | 0.644 | 0.417 | 559 |
| grep_a025_l30 | 0.293 | 0.523 | 0.613 | 0.551 | 0.640 | 0.409 | 559 |
| grep_a025_l90 | 0.294 | 0.522 | 0.613 | 0.549 | 0.640 | 0.409 | 559 |
| grep_a000_l30 | 0.286 | 0.524 | 0.611 | 0.553 | 0.639 | 0.405 | 559 |
| grep_a050_l30 | 0.287 | 0.522 | 0.609 | 0.547 | 0.637 | 0.406 | 559 |
| grep_a050_l90 | 0.288 | 0.525 | 0.609 | 0.551 | 0.635 | 0.407 | 559 |
| grep_a000_l90 | 0.286 | 0.523 | 0.608 | 0.553 | 0.635 | 0.403 | 559 |
| grep_a025_l0 | 0.296 | 0.520 | 0.608 | 0.547 | 0.633 | 0.411 | 559 |
| grep_a050_l0 | 0.293 | 0.523 | 0.606 | 0.551 | 0.631 | 0.409 | 559 |
| grep_a075_l90 | 0.285 | 0.521 | 0.606 | 0.547 | 0.633 | 0.404 | 559 |
| grep_a075_l30 | 0.285 | 0.521 | 0.606 | 0.547 | 0.633 | 0.404 | 559 |
| grep_a000_l0 | 0.285 | 0.522 | 0.605 | 0.549 | 0.631 | 0.403 | 559 |
| grep_a075_l0 | 0.289 | 0.521 | 0.604 | 0.547 | 0.631 | 0.406 | 559 |
| grep_a100_l0 | 0.286 | 0.511 | 0.598 | 0.537 | 0.624 | 0.398 | 559 |
| grep | 0.190 | 0.425 | 0.527 | 0.451 | 0.555 | 0.307 | 559 |
| bm25 | 0.160 | 0.373 | 0.508 | 0.403 | 0.538 | 0.277 | 559 |

## E1 orthogonality (median Jaccard of top-10 neighbours)

| repo | median | mean | files |
|---|---|---|---|
| avantifellows/quiz-backend | 0.182 | 0.194 | 3 |
| rwth-i6/sisyphus | 0.176 | 0.181 | 29 |
| Open-MSS/MSS | 0.077 | 0.140 | 111 |
| tardis-sn/tardis | 0.083 | 0.120 | 125 |
| sopel-irc/sopel | 0.154 | 0.185 | 38 |
| dmlc/dgl | 0.083 | 0.131 | 239 |
| pypa/pip | 0.118 | 0.164 | 349 |
| gammasim/simtools | 0.083 | 0.111 | 81 |
| ctc-oss/fapolicy-analyzer | 0.167 | 0.181 | 79 |
| okta/okta-jwt-verifier-python | 0.455 | 0.490 | 11 |
| gitpython-developers/GitPython | 0.133 | 0.160 | 59 |
| huggingface/optimum-benchmark | 0.167 | 0.156 | 62 |
| JoinMarket-Org/joinmarket-clientserver | 0.154 | 0.137 | 16 |
| TagStudioDev/TagStudio | 0.167 | 0.177 | 7 |
| micropython/micropython-lib | 0.083 | 0.293 | 7 |
| Bears-R-Us/arkouda | 0.250 | 0.257 | 30 |
| aiortc/aiortc | 0.154 | 0.174 | 44 |
| mathesar-foundation/mathesar | 0.143 | 0.158 | 217 |
| JackPlowman/repo_standards_validator | 0.500 | 0.444 | 5 |
| python/cpython | 0.143 | 0.172 | 149 |
| numba/numba | 0.071 | 0.087 | 487 |
| jobatabs/textec | 0.300 | 0.333 | 7 |
| webcompat/webcompat.com | 0.273 | 0.258 | 8 |
| airbnb/knowledge-repo | 0.091 | 0.133 | 39 |
| pulp/pulp_rpm | 0.053 | 0.096 | 35 |
| duncanscanga/VDRS-Solutions | 0.429 | 0.486 | 5 |
| plone/plone.restapi | 0.062 | 0.091 | 113 |
| openwisp/openwisp-users | 0.182 | 0.188 | 24 |
| rucio/rucio | 0.059 | 0.079 | 293 |
| jazzband/django-two-factor-auth | 0.182 | 0.220 | 20 |
| netbox-community/netbox | 0.176 | 0.232 | 60 |
| Innopoints/backend | 0.100 | 0.187 | 33 |
| pyca/pyopenssl | 0.286 | 0.300 | 8 |
| matchms/matchms-backup | 0.083 | 0.171 | 32 |
| latchset/jwcrypto | 0.571 | 0.549 | 6 |
| justin13601/ACES | 0.300 | 0.320 | 11 |
| jupyterhub/oauthenticator | 0.176 | 0.134 | 10 |
| PlasmaPy/PlasmaPy | 0.071 | 0.100 | 121 |
| fractal-analytics-platform/fractal-tasks-core | 0.071 | 0.154 | 73 |
| OpenEnergyPlatform/open-MaStR | 0.231 | 0.244 | 16 |
| UCL/TLOmodel | 0.000 | 0.061 | 192 |
| Deltares/imod-python | 0.111 | 0.146 | 192 |
| Project-MONAI/MONAI | 0.077 | 0.094 | 676 |
| ivadomed/ivadomed | 0.083 | 0.126 | 58 |
| xCDAT/xcdat | 0.308 | 0.332 | 18 |
| ansys/pymapdl | 0.182 | 0.185 | 48 |
| CrossGL/crosstl | 0.071 | 0.094 | 15 |
| ckan/ckan | 0.062 | 0.085 | 306 |
| fulcrumgenomics/prymer | 0.222 | 0.249 | 22 |
| intelowlproject/GreedyBear | 0.167 | 0.177 | 20 |
| spacetelescope/stcal | 0.273 | 0.328 | 14 |
| CWorthy-ocean/roms-tools | 0.143 | 0.167 | 27 |
| twisted/klein | 0.231 | 0.272 | 37 |
| traceloop/openllmetry | 0.300 | 0.300 | 1 |
| celery/django-celery-beat | 0.300 | 0.274 | 9 |
| NCSU-High-Powered-Rocketry-Club/AirbrakesV2 | 0.200 | 0.259 | 36 |
| cupy/cupy | 0.083 | 0.148 | 77 |
| Happy-Algorithms-League/hal-cgp | 0.300 | 0.307 | 11 |
| sgkit-dev/sgkit | 0.154 | 0.177 | 41 |
| Ouranosinc/xclim | 0.182 | 0.220 | 40 |
| tarantool/ansible-cartridge | 0.053 | 0.053 | 1 |
| rapidsai/dask-cuda | 0.455 | 0.398 | 5 |
| oppia/oppia | 0.000 | 0.028 | 438 |
| freedomofpress/securedrop-client | 0.300 | 0.294 | 33 |
| azavea/raster-vision | 0.067 | 0.078 | 117 |
| zarr-developers/zarr-python | 0.333 | 0.343 | 24 |
| paperless-ngx/paperless-ngx | 0.133 | 0.154 | 52 |
| TransformerLensOrg/TransformerLens | 0.273 | 0.304 | 15 |
| NatLibFi/Annif | 0.062 | 0.124 | 56 |
| alexa-pi/AlexaPi | 0.273 | 0.289 | 5 |
| cisagov/manage.get.gov | 0.167 | 0.241 | 59 |
| Agenta-AI/agenta | 0.053 | 0.108 | 32 |
| matrix-org/synapse | 0.071 | 0.098 | 502 |
| NVIDIA/NeMo | 0.077 | 0.116 | 925 |
| Delgan/loguru | 0.111 | 0.138 | 8 |
| facebookresearch/xformers | 0.182 | 0.222 | 81 |
| stanfordnlp/dspy | 0.100 | 0.155 | 137 |
| conan-io/conan | 0.083 | 0.116 | 299 |
| pylint-dev/pylint | 0.062 | 0.079 | 212 |
| secdev/scapy | 0.133 | 0.158 | 282 |
| rq/rq | 0.267 | 0.290 | 46 |
| cython/cython | 0.111 | 0.159 | 90 |
| sphinx-doc/sphinx | 0.067 | 0.117 | 182 |
| ansible/ansible | 0.071 | 0.100 | 513 |
| iterative/dvc | 0.077 | 0.107 | 322 |
| scrapy/scrapy | 0.071 | 0.080 | 228 |
| instructor-ai/instructor | 0.182 | 0.220 | 42 |
| Zulko/moviepy | 0.154 | 0.163 | 53 |
| gaogaotiantian/viztracer | 0.083 | 0.129 | 29 |
| locustio/locust | 0.143 | 0.172 | 52 |
| vitalik/django-ninja | 0.083 | 0.137 | 64 |
| nltk/nltk | 0.077 | 0.096 | 211 |
| albumentations-team/albumentations | 0.111 | 0.139 | 55 |
| robotframework/robotframework | 0.083 | 0.126 | 260 |
| ShishirPatil/gorilla | 0.400 | 0.400 | 1 |
| Netflix/metaflow | 0.154 | 0.178 | 190 |
| optuna/optuna | 0.100 | 0.139 | 205 |
| explodinggradients/ragas | 0.143 | 0.152 | 73 |
| kornia/kornia | 0.071 | 0.122 | 355 |
| internetarchive/openlibrary | 0.083 | 0.120 | 130 |
| AzureAD/microsoft-authentication-library-for-python | 0.231 | 0.258 | 16 |
| home-assistant/core | 0.077 | 0.101 | 1169 |
| zulip/zulip | 0.111 | 0.144 | 388 |
| kedro-org/kedro | 0.154 | 0.161 | 81 |
| nautobot/nautobot | 0.056 | 0.078 | 346 |
| Standard-Labs/real-intent | 0.300 | 0.330 | 8 |
| feast-dev/feast | 0.062 | 0.080 | 3 |
| spotify/luigi | 0.125 | 0.138 | 131 |
| BerriAI/litellm | 0.176 | 0.186 | 333 |
| networkx/networkx | 0.000 | 0.074 | 263 |
| wandb/wandb | 0.083 | 0.127 | 350 |
| speechbrain/speechbrain | 0.000 | 0.058 | 233 |
| sktime/sktime | 0.077 | 0.115 | 736 |
| UXARRAY/uxarray | 0.176 | 0.223 | 59 |
| Chainlit/chainlit | 0.500 | 0.400 | 2 |
| mesonbuild/meson | 0.077 | 0.126 | 193 |
| fortra/impacket | 0.071 | 0.093 | 177 |
| huggingface/accelerate | 0.176 | 0.187 | 97 |
| ranaroussi/yfinance | 0.176 | 0.211 | 22 |
| SYSTRAN/faster-whisper | 0.333 | 0.404 | 3 |
| streamlit/streamlit | 0.077 | 0.115 | 236 |
| Lightning-AI/pytorch-lightning | 0.053 | 0.075 | 368 |
| bridgecrewio/checkov | 0.083 | 0.107 | 2052 |
| py-pdf/pypdf | 0.176 | 0.199 | 57 |
| matplotlib/matplotlib | 0.067 | 0.086 | 252 |
| numpy/numpy | 0.077 | 0.110 | 241 |
| aio-libs/aiohttp | 0.111 | 0.143 | 68 |
| mlflow/mlflow | 0.083 | 0.122 | 771 |
| phidatahq/phidata | 0.000 | 0.087 | 485 |
| ultralytics/ultralytics | 0.111 | 0.129 | 121 |
| sqlfluff/sqlfluff | 0.071 | 0.110 | 234 |
| Qiskit/qiskit | 0.077 | 0.108 | 976 |
| getmoto/moto | 0.125 | 0.146 | 770 |
| pydantic/pydantic | 0.167 | 0.177 | 109 |
| huggingface/trl | 0.083 | 0.107 | 52 |
| sympy/sympy | 0.059 | 0.091 | 1267 |
| scipy/scipy | 0.154 | 0.175 | 220 |
| DS4SD/docling | 0.200 | 0.226 | 50 |
| keras-team/keras | 0.053 | 0.082 | 276 |
| UKPLab/sentence-transformers | 0.071 | 0.083 | 99 |
| python/mypy | 0.176 | 0.183 | 244 |
| modin-project/modin | 0.111 | 0.150 | 198 |
| prowler-cloud/prowler | 0.083 | 0.125 | 1410 |
| ray-project/ray | 0.375 | 0.421 | 13 |
| huggingface/transformers | 0.067 | 0.095 | 1518 |
| PrefectHQ/prefect | 0.111 | 0.130 | 397 |
| jax-ml/jax | 0.000 | 0.063 | 471 |
| huggingface/diffusers | 0.053 | 0.076 | 845 |
| scikit-learn/scikit-learn | 0.053 | 0.072 | 603 |
| dask/dask | 0.143 | 0.152 | 168 |
| pandas-dev/pandas | 0.053 | 0.063 | 767 |
| vllm-project/vllm | 0.154 | 0.169 | 238 |
| yt-dlp/yt-dlp | 0.077 | 0.080 | 461 |
| django/django | 0.071 | 0.093 | 1334 |
| roboflow/supervision | 0.214 | 0.251 | 49 |

## R@10 by repo: BM25 vs best hybrid

| repo | n | bm25 | best hybrid | Δ | best cfg |
|---|---|---|---|---|---|
| Agenta-AI/agenta | 1 | 0.667 | 1.000 | +0.333 | grep_a025_l30 |
| AzureAD/microsoft-authentication-library-for-python | 2 | 0.500 | 0.500 | +0.000 | bm25_a000_l90 |
| Bears-R-Us/arkouda | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| BerriAI/litellm | 2 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| CWorthy-ocean/roms-tools | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| Chainlit/chainlit | 3 | 0.833 | 1.000 | +0.167 | bm25_a000_l90 |
| CrossGL/crosstl | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| DS4SD/docling | 8 | 0.250 | 0.500 | +0.250 | grep_a025_l30 |
| Delgan/loguru | 1 | 0.000 | 1.000 | +1.000 | grep_a025_l30 |
| Deltares/imod-python | 1 | 0.333 | 1.000 | +0.667 | grep_a025_l30 |
| Happy-Algorithms-League/hal-cgp | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| Innopoints/backend | 1 | 0.000 | 0.500 | +0.500 | bm25_a000_l90 |
| JackPlowman/repo_standards_validator | 1 | 0.500 | 0.500 | +0.000 | bm25_a000_l90 |
| JoinMarket-Org/joinmarket-clientserver | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| Lightning-AI/pytorch-lightning | 4 | 0.500 | 0.750 | +0.250 | bm25_a000_l90 |
| NCSU-High-Powered-Rocketry-Club/AirbrakesV2 | 1 | 0.500 | 0.500 | +0.000 | bm25_a000_l90 |
| NVIDIA/NeMo | 1 | 0.000 | 1.000 | +1.000 | bm25_a000_l90 |
| NatLibFi/Annif | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| Netflix/metaflow | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| Open-MSS/MSS | 1 | 0.000 | 0.000 | +0.000 | bm25_a000_l90 |
| OpenEnergyPlatform/open-MaStR | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| Ouranosinc/xclim | 1 | 0.600 | 0.800 | +0.200 | bm25_a000_l90 |
| PlasmaPy/PlasmaPy | 1 | 0.000 | 1.000 | +1.000 | bm25_a000_l90 |
| PrefectHQ/prefect | 16 | 0.625 | 0.688 | +0.062 | bm25_a000_l90 |
| Project-MONAI/MONAI | 1 | 0.000 | 0.000 | +0.000 | bm25_a000_l90 |
| Qiskit/qiskit | 6 | 0.833 | 1.000 | +0.167 | bm25_a000_l90 |
| SYSTRAN/faster-whisper | 3 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| ShishirPatil/gorilla | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| Standard-Labs/real-intent | 2 | 0.500 | 0.500 | +0.000 | bm25_a000_l90 |
| TagStudioDev/TagStudio | 1 | 0.000 | 1.000 | +1.000 | grep_a025_l30 |
| TransformerLensOrg/TransformerLens | 1 | 0.667 | 1.000 | +0.333 | grep_a025_l30 |
| UCL/TLOmodel | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| UKPLab/sentence-transformers | 8 | 0.750 | 1.000 | +0.250 | grep_a050_l30 |
| UXARRAY/uxarray | 3 | 0.444 | 0.556 | +0.111 | bm25_a000_l90 |
| Zulko/moviepy | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| aio-libs/aiohttp | 5 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| aiortc/aiortc | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| airbnb/knowledge-repo | 1 | 0.000 | 0.000 | +0.000 | bm25_a000_l90 |
| albumentations-team/albumentations | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| alexa-pi/AlexaPi | 1 | 0.500 | 0.500 | +0.000 | bm25_a000_l90 |
| ansible/ansible | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| ansys/pymapdl | 1 | 0.000 | 1.000 | +1.000 | grep_a025_l30 |
| avantifellows/quiz-backend | 1 | 0.500 | 1.000 | +0.500 | bm25_a050_l0 |
| azavea/raster-vision | 1 | 0.333 | 0.333 | +0.000 | bm25_a000_l90 |
| bridgecrewio/checkov | 4 | 0.750 | 0.750 | +0.000 | bm25_a000_l90 |
| celery/django-celery-beat | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| certbot/certbot | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| cisagov/manage.get.gov | 1 | 0.000 | 0.333 | +0.333 | grep_a025_l30 |
| ckan/ckan | 1 | 0.000 | 0.000 | +0.000 | bm25_a000_l90 |
| conan-io/conan | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| ctc-oss/fapolicy-analyzer | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| cupy/cupy | 1 | 0.333 | 0.667 | +0.333 | bm25_a000_l90 |
| cython/cython | 1 | 0.000 | 1.000 | +1.000 | bm25_a000_l90 |
| dask/dask | 20 | 0.700 | 0.800 | +0.100 | bm25_a050_l0 |
| django/django | 35 | 0.457 | 0.629 | +0.171 | bm25_a000_l90 |
| dmlc/dgl | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| duncanscanga/VDRS-Solutions | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| explodinggradients/ragas | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| facebookresearch/xformers | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| feast-dev/feast | 2 | 0.500 | 1.000 | +0.500 | bm25_a000_l90 |
| flet-dev/flet | 8 | 0.625 | 0.875 | +0.250 | grep_a025_l30 |
| fortra/impacket | 3 | 0.500 | 0.667 | +0.167 | grep_a025_l30 |
| fractal-analytics-platform/fractal-tasks-core | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| freedomofpress/securedrop-client | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| fulcrumgenomics/prymer | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| gammasim/simtools | 1 | 0.333 | 0.333 | +0.000 | bm25_a000_l90 |
| gaogaotiantian/viztracer | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| getmoto/moto | 6 | 0.667 | 0.833 | +0.167 | grep_a025_l30 |
| gitpython-developers/GitPython | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| home-assistant/core | 2 | 0.375 | 0.625 | +0.250 | bm25_a000_l90 |
| huggingface/accelerate | 3 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| huggingface/diffusers | 17 | 0.294 | 0.412 | +0.118 | bm25_a050_l0 |
| huggingface/optimum-benchmark | 1 | 0.000 | 0.000 | +0.000 | bm25_a000_l90 |
| huggingface/transformers | 15 | 0.422 | 0.667 | +0.244 | grep_a025_l30 |
| huggingface/trl | 6 | 0.833 | 0.833 | +0.000 | bm25_a000_l90 |
| hyeneung/tech-blog-hub-site | 1 | 0.500 | 1.000 | +0.500 | grep_a025_l30 |
| instructor-ai/instructor | 1 | 0.000 | 1.000 | +1.000 | grep_a025_l30 |
| intelowlproject/GreedyBear | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| internetarchive/openlibrary | 2 | 0.500 | 1.000 | +0.500 | bm25_a000_l90 |
| iterative/dvc | 1 | 0.000 | 1.000 | +1.000 | bm25_a000_l90 |
| ivadomed/ivadomed | 1 | 0.333 | 0.667 | +0.333 | grep_a025_l30 |
| jax-ml/jax | 17 | 0.471 | 0.882 | +0.412 | grep_a025_l30 |
| jazzband/django-two-factor-auth | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| jobatabs/textec | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| jupyterhub/oauthenticator | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| justin13601/ACES | 1 | 0.000 | 0.333 | +0.333 | bm25_a000_l90 |
| kedro-org/kedro | 2 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| keras-team/keras | 8 | 0.750 | 0.750 | +0.000 | bm25_a000_l90 |
| kiasambrook/tfl-live-tracker | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| kornia/kornia | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| langchain-ai/langgraph | 3 | 0.667 | 1.000 | +0.333 | grep_a025_l30 |
| latchset/jwcrypto | 1 | 0.000 | 1.000 | +1.000 | bm25_a000_l90 |
| locustio/locust | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| matchms/matchms-backup | 1 | 0.250 | 0.250 | +0.000 | bm25_a000_l90 |
| mathesar-foundation/mathesar | 1 | 0.000 | 0.000 | +0.000 | bm25_a000_l90 |
| matplotlib/matplotlib | 5 | 0.800 | 0.800 | +0.000 | bm25_a000_l90 |
| matrix-org/synapse | 1 | 0.500 | 0.500 | +0.000 | bm25_a000_l90 |
| mesonbuild/meson | 3 | 0.333 | 0.667 | +0.333 | grep_a025_l30 |
| micropython/micropython-lib | 1 | 0.000 | 1.000 | +1.000 | grep_a025_l30 |
| mlflow/mlflow | 5 | 0.200 | 0.600 | +0.400 | grep_a025_l30 |
| modin-project/modin | 12 | 0.479 | 0.611 | +0.132 | grep_a025_l30 |
| nautobot/nautobot | 2 | 0.000 | 0.000 | +0.000 | bm25_a000_l90 |
| netbox-community/netbox | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| networkx/networkx | 2 | 0.500 | 0.500 | +0.000 | bm25_a000_l90 |
| nltk/nltk | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| numba/numba | 1 | 0.000 | 1.000 | +1.000 | bm25_a000_l90 |
| numpy/numpy | 5 | 0.200 | 0.400 | +0.200 | grep_a025_l30 |
| okta/okta-jwt-verifier-python | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| openwisp/openwisp-users | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| oppia/oppia | 1 | 0.000 | 0.000 | +0.000 | bm25_a000_l90 |
| optuna/optuna | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| pandas-dev/pandas | 22 | 0.258 | 0.712 | +0.455 | grep_a025_l30 |
| paperless-ngx/paperless-ngx | 1 | 0.000 | 1.000 | +1.000 | bm25_a000_l90 |
| phidatahq/phidata | 5 | 0.800 | 0.800 | +0.000 | grep_a025_l30 |
| plone/plone.restapi | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| pm4-graders/3ES | 1 | 0.500 | 1.000 | +0.500 | bm25_a050_l0 |
| prowler-cloud/prowler | 12 | 0.083 | 0.417 | +0.333 | bm25_a100_l0 |
| pulp/pulp_rpm | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| py-pdf/pypdf | 4 | 0.750 | 0.750 | +0.000 | bm25_a000_l90 |
| pyca/pyopenssl | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| pydantic/pydantic | 6 | 0.333 | 0.667 | +0.333 | grep_a025_l30 |
| pylint-dev/pylint | 1 | 0.000 | 1.000 | +1.000 | bm25_a000_l90 |
| pypa/pip | 1 | 0.000 | 1.000 | +1.000 | bm25_a000_l90 |
| python/cpython | 1 | 0.000 | 0.000 | +0.000 | bm25_a000_l90 |
| python/mypy | 11 | 0.273 | 0.636 | +0.364 | grep_a025_l30 |
| ranaroussi/yfinance | 3 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| rapidsai/dask-cuda | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| ray-project/ray | 14 | 0.643 | 0.714 | +0.071 | bm25_a000_l90 |
| roboflow/supervision | 2 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| robotframework/robotframework | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| rq/rq | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| rucio/rucio | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| rwth-i6/sisyphus | 1 | 0.000 | 0.500 | +0.500 | grep_a025_l30 |
| sancus-tee/sancus-compiler | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| scikit-learn/scikit-learn | 19 | 0.474 | 0.632 | +0.158 | bm25_a000_l30 |
| scipy/scipy | 8 | 0.625 | 0.875 | +0.250 | bm25_a000_l90 |
| scrapy/scrapy | 1 | 0.000 | 0.000 | +0.000 | bm25_a000_l90 |
| secdev/scapy | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| sgkit-dev/sgkit | 1 | 0.000 | 0.000 | +0.000 | bm25_a000_l90 |
| sktime/sktime | 2 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| sopel-irc/sopel | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| spacetelescope/stcal | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| speechbrain/speechbrain | 2 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| sphinx-doc/sphinx | 1 | 0.000 | 0.000 | +0.000 | bm25_a000_l90 |
| spotify/luigi | 2 | 0.500 | 1.000 | +0.500 | grep_a025_l30 |
| sqlfluff/sqlfluff | 6 | 0.333 | 0.500 | +0.167 | bm25_a000_l90 |
| stanfordnlp/dspy | 1 | 0.000 | 1.000 | +1.000 | bm25_a000_l90 |
| streamlit/streamlit | 4 | 0.917 | 0.917 | +0.000 | bm25_a000_l90 |
| sympy/sympy | 7 | 0.429 | 0.714 | +0.286 | bm25_a000_l90 |
| tarantool/ansible-cartridge | 1 | 0.000 | 0.000 | +0.000 | bm25_a000_l90 |
| tardis-sn/tardis | 1 | 0.500 | 0.500 | +0.000 | bm25_a000_l90 |
| tobymao/sqlglot | 15 | 0.867 | 1.000 | +0.133 | bm25_a000_l90 |
| traceloop/openllmetry | 1 | 0.000 | 0.000 | +0.000 | bm25_a000_l90 |
| twisted/klein | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| ultralytics/ultralytics | 6 | 0.167 | 0.500 | +0.333 | grep_a025_l30 |
| una-auxme/paf | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| vitalik/django-ninja | 1 | 0.000 | 1.000 | +1.000 | bm25_a050_l0 |
| vllm-project/vllm | 24 | 0.271 | 0.406 | +0.135 | grep_a025_l30 |
| wandb/wandb | 2 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| webcompat/webcompat.com | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| xCDAT/xcdat | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| yt-dlp/yt-dlp | 27 | 0.000 | 0.370 | +0.370 | grep_a025_l30 |
| zarr-developers/zarr-python | 1 | 1.000 | 1.000 | +0.000 | bm25_a000_l90 |
| zulip/zulip | 2 | 0.000 | 0.000 | +0.000 | bm25_a000_l90 |