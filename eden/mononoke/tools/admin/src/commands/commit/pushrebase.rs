/*
 * Copyright (c) Meta Platforms, Inc. and affiliates.
 *
 * This software may be used and distributed according to the terms of the
 * GNU General Public License version 2.
 */

use std::collections::HashSet;

use anyhow::Error;
use anyhow::Result;
use blobstore::Loadable;
use bookmarks::BookmarkName;
use clap::Args;
use context::CoreContext;
use futures::stream;
use futures::StreamExt;
use futures::TryFutureExt;
use futures::TryStreamExt;
use metaconfig_types::BookmarkAttrs;
use metaconfig_types::RepoConfigRef;
use repo_blobstore::RepoBlobstoreRef;

use super::Repo;
use crate::commit_id::parse_commit_id;

#[derive(Args)]
pub struct CommitPushrebaseArgs {
    /// Destination Bookmark to pushrebase onto
    #[clap(long, short = 'B')]
    bookmark: BookmarkName,

    /// Source Commit ID to pushrebase (bottom of the stack if pushrebasing a stack)
    #[clap(long, short = 's')]
    source: String,

    /// Top Commit ID of the source stack, if pushrebasing a stack
    #[clap(long, short = 't')]
    top: Option<String>,
}

pub async fn pushrebase(
    ctx: &CoreContext,
    repo: &Repo,
    pushrebase_args: CommitPushrebaseArgs,
) -> Result<()> {
    let source = parse_commit_id(ctx, repo, &pushrebase_args.source).await?;

    let csids = if let Some(top) = &pushrebase_args.top {
        let top = parse_commit_id(ctx, repo, top).await?;
        super::resolve_stack(ctx, repo, source, top).await?
    } else {
        vec![source]
    };

    let pushrebase_flags = repo.repo_config().pushrebase.flags;
    let bookmark_attrs = BookmarkAttrs::new(ctx.fb, repo.repo_config().bookmarks.clone()).await?;
    let pushrebase_hooks = bookmarks_movement::get_pushrebase_hooks(
        ctx,
        repo,
        &pushrebase_args.bookmark,
        &bookmark_attrs,
        &repo.repo_config().pushrebase,
    )
    .map_err(Error::from)?;

    let bonsais = stream::iter(csids)
        .map(|csid| async move {
            csid.load(ctx, repo.repo_blobstore())
                .map_err(Error::from)
                .await
        })
        .buffered(100)
        .try_collect::<HashSet<_>>()
        .await?;

    let result = pushrebase::do_pushrebase_bonsai(
        ctx,
        repo,
        &pushrebase_flags,
        &pushrebase_args.bookmark,
        &bonsais,
        &pushrebase_hooks,
    )
    .map_err(Error::from)
    .await?;

    println!("{}", result.head);

    Ok(())
}