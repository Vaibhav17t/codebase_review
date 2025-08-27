# Example of well-structured code

from dataclasses import dataclass
from typing import Optional

@dataclass
class User:
    name: str
    email: str
    age: int
    # Well-structured data instead of many parameters

class UserProcessor:
    def process(self, user: User) -> bool:
        """Clean, focused function"""
        if not self._validate_user(user):
            return False
        
        return self._save_user(user)
    
    def _validate_user(self, user: User) -> bool:
        return user.age >= 18 and "@" in user.email
    
    def _save_user(self, user: User) -> bool:
        # Implementation here
        return True
