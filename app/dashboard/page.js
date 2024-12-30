"use client";

import React from "react";
import { signOut, useSession } from "next-auth/react";

const page = () => {
  const { data: session } = useSession();

  return (
    <div className="center">
      <div className="form-col">
        {session?.user?.username} | userID: {session?.user?.userId}
        <button className="btn" onClick={signOut}>
          sign out
        </button>
      </div>
    </div>
  );
};

export default page;
