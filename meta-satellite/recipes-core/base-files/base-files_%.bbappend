#inherit extrausers


#INHERIT += "extrausers"

#ROOT_HASH="\$5\$LAqcfy8nE2kQ0q6b\$wfO1JnGimkdjXY0UrT4gj08NjvAvK6XTPbF3x65h7U7"
#USER_HASH="\$5\$LAqcfy8nE2kQ0q6b\$wfO1JnGimkdjXY0UrT4gj08NjvAvK6XTPbF3x65h7U7"

# Ensure groups exist and create user esat93 (adjust UID/GID)


#EXTRA_USERS_PARAMS:append = "\
#    usermod -p '${ROOT_HASH}' root; \
#    usermod -s /bin/bash root; \
#    useradd -p '${USER_HASH}' -s /bin/bash -m esat93; \
#    groupadd -r i2c; \
#    groupadd -r spi; \
#    groupadd -r gpio; \
#    groupadd -r plugdev; \
#    groupadd -r can; \
#    usermod -a -G i2c,spi,gpio,plugdev,can,dialout,video,audio,tty,sudo esat93; \
#"
