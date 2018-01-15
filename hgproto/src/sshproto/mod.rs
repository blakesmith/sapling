// Copyright (c) 2004-present, Facebook, Inc.
// All Rights Reserved.
//
// This software may be used and distributed according to the terms of the
// GNU General Public License version 2 or any later version.

//! SSH/stdio line-oriented protocol
//!
//! References are https://www.mercurial-scm.org/wiki/SshCommandProtocol and
//! https://www.mercurial-scm.org/wiki/WireProtocol though they're scant on detail.
//!
//! The encoding is:
//! ```
//! command := <command> '\n' <key-value>{N}
//! key-value := star | kv
//! star := '*' ' ' <count> kv{count}
//! kv := <name> ' ' <numbytes> '\n' <byte>{numbytes}
//! ```
//!
//! Where `N` is the specific number of `<key-value>` pairs expected by the command.
//!
//! The types of the values are implied by the command rather than explicitly encoded.
//!
//! pair := <hash> '-' <hash>
//! list := (<hash> ' ')* <item>
//!
//! Responses to commands are always:
//! ```
//! <numbytes> '\n'
//! <byte>{numbytes}
//! ```
//!
//! Each command has its own encoding of the response.

use bytes::BytesMut;
use tokio_io::codec::Decoder;

use {Request, Response};
use handler::{OutputStream, ResponseEncoder};

use errors::*;

pub mod request;
pub mod response;

#[derive(Clone)]
pub struct HgSshCommandEncode;
#[derive(Clone)]
pub struct HgSshCommandDecode;

impl ResponseEncoder for HgSshCommandEncode {
    fn encode(&self, response: Response) -> OutputStream {
        response::encode(response)
    }
}

impl Decoder for HgSshCommandDecode {
    type Item = Request;
    type Error = Error;

    fn decode(&mut self, buf: &mut BytesMut) -> Result<Option<Request>> {
        request::parse_request(buf)
    }
}
