"use client";

import React from "react";
import { signOut, useSession } from "next-auth/react";
import RenewCode from "@/components/RenewCode";

const page = () => {
  const { data: session } = useSession();

  return (
    <div className="center">
      <div className="form-col max-w-fit">
        {session?.user?.expired ? (
          <RenewCode />
        ) : (
          <div className="flex flex-col justify-center items-center">
            <span>
              Subscription <span className="text-green-400">Active</span>
            </span>
            <span>Expired Date: {session?.user?.expiry}</span>
          </div>
        )}
        <button className="btn" onClick={signOut}>
          sign out
        </button>
      </div>
    </div>
  );
};

export default page;
