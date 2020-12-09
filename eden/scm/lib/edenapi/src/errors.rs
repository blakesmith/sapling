/*
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This software may be used and distributed according to the terms of the
 * GNU General Public License version 2.
 */

use std::path::PathBuf;

use thiserror::Error;

use edenapi_types::wire::WireToApiConversionError;
use http_client::HttpClientError;

#[derive(Debug, Error)]
pub enum EdenApiError {
    #[error("Failed to serialize request: {0}")]
    RequestSerializationFailed(#[source] serde_cbor::Error),
    #[error(transparent)]
    BadConfig(#[from] ConfigError),
    #[error(transparent)]
    Http(#[from] HttpClientError),
    #[error(transparent)]
    InvalidUrl(#[from] url::ParseError),
    #[error(transparent)]
    WireToApiConversionFailed(#[from] WireToApiConversionError),
    #[error(transparent)]
    Other(#[from] anyhow::Error),
}

#[derive(Debug, Error)]
pub enum ConfigError {
    #[error("No server URL specified")]
    MissingUrl,
    #[error("TLS certificate or key is missing or invalid: {0:?}")]
    BadCertOrKey(PathBuf),
    #[error("Invalid server URL: {0}")]
    InvalidUrl(#[source] url::ParseError),
    #[error("Config field '{0}' is malformed")]
    Malformed(String, #[source] anyhow::Error),
}
