package io.wispforest.owo.braid.core;

/**
 * Configuration for a {@link BraidScreen}.
 *
 * <p>This is intentionally a <b>top-level</b> class rather than a nested class of
 * {@code BraidScreen}: {@code BraidScreen} extends {@code net.minecraft.client.gui.screens.Screen},
 * so referencing a nested type would drag the client-only {@code Screen} class into the static
 * initialization of any class holding a {@code Settings} field. On a dedicated server that
 * fails with {@code Cannot load class net.minecraft.client.gui.screens.Screen in environment type SERVER}.
 *
 * <p>Keeping the type standalone means server-side code can hold and pass around screen settings
 * without ever touching client-only classes.
 */
public class BraidScreenSettings {

    public boolean shouldPause = true;
    public boolean useBraidAppWidget = true;
}
