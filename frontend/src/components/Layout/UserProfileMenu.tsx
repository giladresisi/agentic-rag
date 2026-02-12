import { useState } from 'react';
import { Settings, LogOut } from 'lucide-react';

interface UserProfileMenuProps {
  user: { email: string } | null;
  onSettingsClick: () => void;
  onLogout: () => void;
}

export function UserProfileMenu({ user, onSettingsClick, onLogout }: UserProfileMenuProps) {
  const [showMenu, setShowMenu] = useState(false);

  if (!user) return null;

  // Get initials from email (first letter)
  const initial = user.email.charAt(0).toUpperCase();

  return (
    <div className="relative">
      {/* Profile menu floating above */}
      {showMenu && (
        <div className="absolute bottom-full mb-2 left-0 bg-background border rounded-md shadow-lg py-1 min-w-[180px]">
          <button
            onClick={() => {
              setShowMenu(false);
              onSettingsClick();
            }}
            className="w-full px-4 py-2 text-left text-sm hover:bg-accent flex items-center gap-2"
          >
            <Settings className="w-4 h-4" />
            Settings
          </button>
          <button
            onClick={() => {
              setShowMenu(false);
              onLogout();
            }}
            className="w-full px-4 py-2 text-left text-sm hover:bg-accent flex items-center gap-2"
          >
            <LogOut className="w-4 h-4" />
            Log out
          </button>
        </div>
      )}

      {/* Profile button */}
      <button
        onClick={() => setShowMenu(!showMenu)}
        className="w-full p-3 hover:bg-accent rounded-lg flex items-center gap-3"
      >
        <div className="w-10 h-10 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-semibold">
          {initial}
        </div>
        <div className="flex-1 text-left text-sm">
          <div className="font-medium">User</div>
          <div className="text-muted-foreground">{user.email}</div>
        </div>
      </button>
    </div>
  );
}
