from fastapi import APIRouter, HTTPException
from bson import ObjectId
from pymongo import MongoClient
from typing import List

from models.PostModel import *
from database import *

# Create router
post_router = APIRouter()

# Create a post with updates to user and subTopiq tables
@post_router.post("/", response_model=Post)
async def create_post(title: str, description: str, creator_id: str, subtopiq_id: str):
    try:
        creator_oid = ObjectId(creator_id)
        subtopiq_oid = ObjectId(subtopiq_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    post_data = {
        "title": title,
        "description": description,
        "upVote": 0,
        "downVote": 0,
        "replies": [],
        "creatorId": creator_oid,
        "subTopiqId": subtopiq_oid,
    }

    result = db.posts.insert_one(post_data)
    post_id = result.inserted_id

    db.users.update_one({"_id": creator_oid}, {"$push": {"posts": {"postId": post_id}}})
    db.subTopiq.update_one({"_id": subtopiq_oid}, {"$push": {"posts": {"postId": post_id}}})

    post_data["id"] = str(post_id)
    post_data["creatorId"] = str(post_data["creatorId"])
    post_data["subTopiqId"] = str(post_data["subTopiqId"])

    return post_data

# View all posts
@post_router.get("/posts", response_model=List[Post])
async def view_all_posts():
    posts = db.posts.find()
    return [
        {
            "id": str(post["_id"]),
            "title": post["title"],
            "description": post["description"],
            "upVote": post["upVote"],
            "downVote": post["downVote"],
            "replies": [{"reply": r["reply"], "creatorId": str(r["creatorId"])} for r in post.get("replies", [])],
            "creatorId": str(post["creatorId"]),
            "subTopiqId": str(post["subTopiqId"]),
        }
        for post in posts
    ]

@post_router.get("/{post_id}", response_model=Post)
async def get_post_by_id(id: str):
    post = db.posts.find_one({"_id": ObjectId(id)})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return {
        "id": str(post["_id"]),
        "title": post["title"],
        "description": post["description"],
        "upVote": post["upVote"],
        "downVote": post["downVote"],
        "replies": [{"reply": r["reply"], "creatorId": str(r["creatorId"])} for r in post.get("replies", [])],
        "creatorId": str(post["creatorId"]),
        "subTopiqId": str(post["subTopiqId"]),
    }

# View posts on a specific subTopiq
@post_router.get("/subtopiq/{subtopiq_id}", response_model=List[Post])
async def view_posts_by_subtopiq(subtopiq_id: str):
    try:
        subtopiq_oid = ObjectId(subtopiq_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid subTopiq ID format")

    posts = db.posts.find({"subTopiqId": subtopiq_oid})
    return [
        {
            "id": str(post["_id"]),
            "title": post["title"],
            "description": post["description"],
            "upVote": post["upVote"],
            "downVote": post["downVote"],
            "replies": [{"reply": r["reply"], "creatorId": str(r["creatorId"])} for r in post.get("replies", [])],
            "creatorId": str(post["creatorId"]),
            "subTopiqId": str(post["subTopiqId"]),
        }
        for post in posts
    ]

# View posts by a specific user
@post_router.get("/creator/{creator_id}", response_model=List[Post])
async def view_posts_by_user(creator_id: str):
    try:
        creator_oid = ObjectId(creator_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid creator ID format")

    posts = db.posts.find({"creatorId": creator_oid})
    return [
        {
            "id": str(post["_id"]),
            "title": post["title"],
            "description": post["description"],
            "upVote": post["upVote"],
            "downVote": post["downVote"],
            "replies": [{"reply": r["reply"], "creatorId": str(r["creatorId"])} for r in post.get("replies", [])],
            "creatorId": str(post["creatorId"]),
            "subTopiqId": str(post["subTopiqId"]),
        }
        for post in posts
    ]

# Reply to a post
@post_router.post("/reply/{post_id}")
async def reply_to_post(post_id: str, reply: str, creator_id: str):
    try:
        post_oid = ObjectId(post_id)
        creator_oid = ObjectId(creator_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    # Check if the post exists
    post = db.posts.find_one({"_id": post_oid})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Create the reply data
    reply_data = {
        "reply": reply,
        "creatorId": creator_oid
    }

    # Add the reply to the post's replies array
    db.posts.update_one(
        {"_id": post_oid},
        {"$push": {"replies": reply_data}}
    )

    return {"message": "Reply added successfully"}


# Upvote a post
@post_router.post("/{post_id}/upvote")
async def upvote_post(post_id: str, user_id: str):
    try:
        post_oid = ObjectId(post_id)
        user_oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    # Check if user has already upvoted the post
    user = db.users.find_one({"_id": user_oid})
    if any(upvote["postId"] == post_oid for upvote in user.get("upVotes", [])):
        raise HTTPException(status_code=400, detail="User has already upvoted this post")

    # Increment upvote count on the post
    db.posts.update_one({"_id": post_oid}, {"$inc": {"upVote": 1}})
    
    # Add post to user's upVotes list
    db.users.update_one({"_id": user_oid}, {"$push": {"upVotes": {"postId": post_oid}}})

    return {"message": "Post upvoted successfully"}

# Downvote a post
@post_router.post("/{post_id}/downvote")
async def downvote_post(post_id: str, user_id: str):
    try:
        post_oid = ObjectId(post_id)
        user_oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    # Check if user has already downvoted the post
    user = db.users.find_one({"_id": user_oid})
    if any(downvote["postId"] == post_oid for downvote in user.get("downVotes", [])):
        raise HTTPException(status_code=400, detail="User has already downvoted this post")

    # Increment downvote count on the post
    db.posts.update_one({"_id": post_oid}, {"$inc": {"downVote": 1}})
    
    # Add post to user's downVotes list
    db.users.update_one({"_id": user_oid}, {"$push": {"downVotes": {"postId": post_oid}}})

    return {"message": "Post downvoted successfully"}


# Get the top 5 most upvoted posts within a specific subTopiq, including creator details
@post_router.get("/top-posts/{subtopiq_id}")
async def get_top_upvoted_posts(subtopiq_id: str):
    try:
        subtopiq_oid = ObjectId(subtopiq_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid subTopiq ID format")
    
    # Pipeline to:
    # 1. Lookup subtopiq id within posts and grep 
    # 2. Sort descending based on upvote
    # 3. Limit to top 5
    # 4. Lookup Users table for creator id and take it as creator info 
    # 5. Aggregate both collections 
    # 6. Format to proper json

    pipeline = [
        {"$match": {"subTopiqId": subtopiq_oid}},
        {"$sort": {"upVote": -1}},
        {"$limit": 5},
        {
            "$lookup": {
                "from": "users",
                "localField": "creatorId",
                "foreignField": "_id",
                "as": "creator_info"
            }
        },
        {"$unwind": "$creator_info"}
    ]

    posts = db.posts.aggregate(pipeline)

    top_posts = [
        {
            "id": str(post["_id"]),
            "title": post["title"],
            "description": post["description"],
            "upVote": post["upVote"],
            "downVote": post["downVote"],
            "replies": [{"reply": r["reply"], "creatorId": str(r["creatorId"])} for r in post.get("replies", [])],
            "creatorId": str(post["creatorId"]),
            "creator_info": {
                "id": str(post["creator_info"]["_id"]),
                "username": post["creator_info"]["username"],
                "email": post["creator_info"]["email"],
                "phone": post["creator_info"]["phone"]
            },
            "subTopiqId": str(post["subTopiqId"]),
        }
        for post in posts
    ]
    print(top_posts)

    return top_posts

# Get all replies for a specific post
@post_router.get("/replies/post/{post_id}", response_model=List[Reply])
async def get_replies_by_post_id(post_id: str):
    try:
        post_oid = ObjectId(post_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid post ID format")

    post = db.posts.find_one({"_id": post_oid})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    return [
        {
            "reply": r["reply"],
            "creatorId": str(r["creatorId"])
        }
        for r in post.get("replies", [])
    ]

# Get all replies by a specific user
@post_router.get("/replies/user/{user_id}", response_model=List[Reply])
async def get_replies_by_user(user_id: str):
    try:
        user_oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    # Find all posts where replies have the given creatorId
    posts = db.posts.find({"replies.creatorId": user_oid})
    user_replies = [
        {
            "reply": reply["reply"],
            "creatorId": str(reply["creatorId"])
        }
        for post in posts
        for reply in post.get("replies", [])
        if reply["creatorId"] == user_oid
    ]

    if not user_replies:
        raise HTTPException(status_code=404, detail="No replies found for this user")

    return user_replies

# Delete a post by ID
@post_router.delete("/{post_id}", response_model=dict)
async def delete_post(post_id: str):
    try:
        post_oid = ObjectId(post_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid post ID format")

    result = db.posts.delete_one({"_id": post_oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Post not found")
    
    return {"message": "Post deleted successfully"}

