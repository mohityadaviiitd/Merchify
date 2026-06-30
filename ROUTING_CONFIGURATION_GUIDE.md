# 🔄 Database Routing Configuration Guide

**Goal**: Show you exactly where to change read/write routing strategy

---

## 📍 Key Files for Routing

### 1️⃣ **PRIMARY: `api/routers.py`** - The Database Router

This is where **ALL** read/write routing decisions happen.

#### **Current Routing Strategy:**

```python
def db_for_read(self, model, **hints):
    """Route READ operations to REPLICAS"""
    user_id = hints.get('user_id') or ShardingContext.get_user_id()
    replica = get_replica_name(user_id)  # ← Returns shard_0_replica or shard_1_replica
    return replica if replica else None

def db_for_write(self, model, **hints):
    """Route WRITE operations to PRIMARY SHARDS"""
    user_id = hints.get('user_id') or ShardingContext.get_user_id()
    shard = get_shard_name(user_id)  # ← Returns shard_0 or shard_1
    return shard if shard else None
```

**Location**: `c:\Users\mohit\Downloads\Merchify\api\routers.py` (Lines 19-55)

---

## 🎯 Common Routing Changes

### **Change #1: Use Primary Shards for ALL Reads (No Replicas)**

**Current**:
```python
# Reads go to replicas
replica = get_replica_name(user_id)  # → shard_0_replica
return replica
```

**Change To**:
```python
# Reads go to primary shards (no replicas)
shard = get_shard_name(user_id)  # → shard_0
return shard
```

**Edit Location**: `api/routers.py` - Line 35

**Before**:
```python
    def db_for_read(self, model, **hints):
        """
        Route read operations to read replicas if available.
        Falls back to primary shard if no context.
        """
        # Try to get user_id from hints (passed explicitly)
        user_id = hints.get('user_id')
        
        # If not in hints, try to get from context
        if user_id is None:
            user_id = ShardingContext.get_user_id()
        
        if user_id is None:
            return None  # Use default database
        
        # Route to replica for read operations (read scaling)
        replica = get_replica_name(user_id)
        return replica if replica else None
```

**After**:
```python
    def db_for_read(self, model, **hints):
        """
        Route read operations to primary shards.
        Uses same shard as writes (no read scaling).
        """
        # Try to get user_id from hints (passed explicitly)
        user_id = hints.get('user_id')
        
        # If not in hints, try to get from context
        if user_id is None:
            user_id = ShardingContext.get_user_id()
        
        if user_id is None:
            return None  # Use default database
        
        # Route to primary shard for read operations
        shard = get_shard_name(user_id)
        return shard if shard else None
```

---

### **Change #2: Use Replicas for ALL Operations (Even Writes)**

⚠️ **NOT RECOMMENDED** - This can cause data consistency issues!

But if you want to do it:

**Edit Location**: `api/routers.py` - Line 49

**Before**:
```python
    def db_for_write(self, model, **hints):
        """
        Route write operations to primary shard only.
        Never write to replicas.
        """
        # Try to get user_id from hints
        user_id = hints.get('user_id')
        
        # If not in hints, try to get from context
        if user_id is None:
            user_id = ShardingContext.get_user_id()
        
        if user_id is None:
            return None  # Use default database
        
        # Always write to primary shard
        shard = get_shard_name(user_id)
        return shard if shard else None
```

**After**:
```python
    def db_for_write(self, model, **hints):
        """
        Route write operations to read replicas.
        WARNING: This can cause replication lag!
        """
        # Try to get user_id from hints
        user_id = hints.get('user_id')
        
        # If not in hints, try to get from context
        if user_id is None:
            user_id = ShardingContext.get_user_id()
        
        if user_id is None:
            return None  # Use default database
        
        # Route to replica (if you really want writes there)
        replica = get_replica_name(user_id)
        return replica if replica else None
```

---

### **Change #3: Custom Routing Logic (Advanced)**

Example: Route specific models differently

**Edit Location**: `api/routers.py` - Modify `db_for_read()` method

**Before**:
```python
    def db_for_read(self, model, **hints):
        user_id = hints.get('user_id') or ShardingContext.get_user_id()
        replica = get_replica_name(user_id)
        return replica if replica else None
```

**After**:
```python
    def db_for_read(self, model, **hints):
        # Special handling for Product model (shared across shards)
        if model.__name__ == 'Product':
            return 'default'  # Products are in default DB
        
        user_id = hints.get('user_id') or ShardingContext.get_user_id()
        
        # Route Order/Cart to replicas
        if model.__name__ in ['Order', 'Cart']:
            replica = get_replica_name(user_id)
            return replica if replica else None
        
        # Default: use replica
        replica = get_replica_name(user_id)
        return replica if replica else None
```

---

### **Change #4: Change Sharding Strategy (User ID → Hash-Based)**

If you want a different distribution strategy, edit **BOTH**:

#### **File 1: `api/sharding.py`** (Lines 56-70)

**Current (Modulo-based)**:
```python
def get_shard_id(user_id: int) -> int:
    """Determine which shard a user belongs to (0-1)"""
    return user_id % SHARD_COUNT  # ← Based on user_id % 2
```

**Change To (Hash-based)**:
```python
def get_shard_id(user_id: int) -> int:
    """Determine which shard a user belongs to (0-1)"""
    import hashlib
    # Hash-based distribution for better randomization
    hash_val = int(hashlib.md5(str(user_id).encode()).hexdigest(), 16)
    return hash_val % SHARD_COUNT
```

#### **File 2: Update `get_shard_name()` and `get_replica_name()` if needed**

Usually no change needed - they use `get_shard_id()` internally.

---

## 📂 ALL Files That Touch Routing

| File | Purpose | Key Functions | Change Impact |
|------|---------|---|---|
| **api/routers.py** | Database router (MAIN) | `db_for_read()`, `db_for_write()` | Direct routing logic |
| **api/sharding.py** | Shard calculation | `get_shard_id()`, `get_shard_name()`, `get_replica_name()` | Shard distribution |
| **api/middleware.py** | Context injection | `ShardingMiddleware` | HOW context is set |
| **merchify_backend/settings.py** | Router registration | `DATABASE_ROUTERS` | WHICH router is used |
| **api/views.py** | View layer | `ShardingContext.set_user_id()` | WHEN context is set |

---

## 🔧 Step-by-Step: Change Read to Use Primary Shards

### Step 1: Open `api/routers.py`

### Step 2: Find the `db_for_read()` method (Lines 19-36)

### Step 3: Change this line:
```python
replica = get_replica_name(user_id)  # ← Change this
return replica if replica else None
```

To:
```python
shard = get_shard_name(user_id)  # ← Changed to primary shard
return shard if shard else None
```

### Step 4: Update the docstring (recommended)
```python
def db_for_read(self, model, **hints):
    """
    Route read operations to primary shards (not replicas).  # ← Updated
    """
```

### Step 5: Test it
```bash
python manage.py check
python manage.py test api.test_sharding
```

---

## 🎲 Change Sharding Distribution Strategy

### **Option A: Even/Odd (Current - user_id % 2)**

**File**: `api/sharding.py`

```python
def get_shard_id(user_id: int) -> int:
    """Current: Modulo 2"""
    return user_id % 2  # 0 or 1
```

**Distribution**: User 1→0, User 2→1, User 3→0, User 4→1... (~50/50)

---

### **Option B: Mod 4 (Distribute to 4 shards)**

```python
SHARD_COUNT = 4
SHARD_NAMES = ['shard_0', 'shard_1', 'shard_2', 'shard_3']

def get_shard_id(user_id: int) -> int:
    """Modulo 4 - 4 shards"""
    return user_id % 4  # 0, 1, 2, or 3
```

**Distribution**: User 1→0, User 2→1, User 3→2, User 4→3, User 5→0... (~25% each)

---

### **Option C: Hash-Based (Consistent Hash)**

```python
def get_shard_id(user_id: int) -> int:
    """Consistent hash distribution"""
    import hashlib
    hash_val = int(hashlib.md5(str(user_id).encode()).hexdigest(), 16)
    return hash_val % SHARD_COUNT
```

**Benefit**: More random distribution, good for load balancing

---

### **Option D: Range-Based**

```python
def get_shard_id(user_id: int) -> int:
    """Range-based: users 1-5000→0, 5001-10000→1, etc."""
    users_per_shard = 5000
    return (user_id - 1) // users_per_shard % SHARD_COUNT
```

**Benefit**: Sequential users on same shard (better cache locality)

---

## 🚨 Important Notes

### **When Routing Decisions Are Made:**

```
Request Flow:
┌─────────────────┐
│ Client Request  │
└────────┬────────┘
         ↓
┌──────────────────────────────────┐
│ api/middleware.py                │
│ ShardingContext.set_user_id(5)   │  ← Context set
└────────┬─────────────────────────┘
         ↓
┌──────────────────────────────────┐
│ api/views.py                     │
│ Order.objects.all()              │  ← Query issued
└────────┬─────────────────────────┘
         ↓
┌──────────────────────────────────┐
│ api/routers.py                   │
│ db_for_read() → shard_0_replica  │  ← ROUTING DECIDED HERE
└────────┬─────────────────────────┘
         ↓
┌──────────────────────────────────┐
│ Database: shard_0_replica        │  ← Query executes here
└──────────────────────────────────┘
```

### **Key Files to Edit for Different Changes:**

| Change Needed | Edit File | Method/Section |
|---|---|---|
| Read replicas → primary | `api/routers.py` | `db_for_read()` |
| Write primary → replica | `api/routers.py` | `db_for_write()` |
| Shard distribution logic | `api/sharding.py` | `get_shard_id()` |
| Add special case routing | `api/routers.py` | `db_for_read/write()` |
| Change shard count | `api/sharding.py` | `SHARD_COUNT`, `SHARD_NAMES` |
| Force specific DB | Views: `Model.objects.using('shard_0')` | Any view |

---

## ⚡ Quick Changes Reference

### **Switch Reads to Primary Shards**
```
File: api/routers.py
Line: 35
Change: get_replica_name(user_id) → get_shard_name(user_id)
```

### **Add Custom Logic for Specific Model**
```
File: api/routers.py
Line: 25 (in db_for_read)
Add: if model.__name__ == 'Product': return 'default'
```

### **Change Shard Distribution**
```
File: api/sharding.py
Line: 59
Change: return user_id % SHARD_COUNT
To: return your_new_logic
```

### **Force Specific Database in View**
```
File: api/views.py
Code: Order.objects.using('shard_0').filter(...)
```

---

## ✅ Testing After Changes

Always run:

```bash
# Check for syntax errors
python manage.py check

# Run sharding tests
python manage.py test api.test_sharding -v 2

# Verify router behavior
python manage.py shell
```

```python
# In Django shell
from api.routers import ShardRouter
from api.sharding import ShardingContext, get_shard_name, get_replica_name
from api.models import Order

# Test routing
ShardingContext.set_user_id(5)
router = ShardRouter()

# Check read routing
read_db = router.db_for_read(Order)
print(f"User 5 reads from: {read_db}")

# Check write routing
write_db = router.db_for_write(Order)
print(f"User 5 writes to: {write_db}")

ShardingContext.clear()
```

Expected output for user 5 (5 % 2 = 1):
```
User 5 reads from: shard_1_replica
User 5 writes to: shard_1
```

---

## Summary

**To change routing, modify these files in order of priority:**

1. **`api/routers.py`** (Lines 19-55)
   - Change `db_for_read()` and/or `db_for_write()` methods
   - Immediate effect on all queries

2. **`api/sharding.py`** (Lines 56-70)
   - Change `get_shard_id()` logic for distribution strategy
   - Affects which shard users get assigned to

3. **`api/middleware.py`** - Usually no changes needed
   - Only if you want different context behavior

4. **Views** - For one-off overrides
   - Use `.using('shard_0')` to force specific database

That's it! The router is the gatekeeper for all database decisions.
