package io.wispforest.owo.samples.braid;

import net.fabricmc.api.EnvType;
import net.fabricmc.api.Environment;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.level.Level;

/**
 * Item that opens the braid sample browser.
 *
 * <p>All client-only code lives in {@link BraidSamplesClient}: this class must stay loadable on a
 * dedicated server. A field or static initializer of this class that referenced a client-only type
 * would make the JVM resolve that class during initialization, which fails on a server with
 * {@code Cannot load class net.minecraft.client.gui.screens.Screen in environment type SERVER}.
 */
public class BraidSamplesItem extends Item {

    public BraidSamplesItem(Properties settings) {
        super(settings);
    }

    @Override
    @Environment(EnvType.CLIENT)
    public InteractionResult use(Level level, Player user, InteractionHand hand) {
        if (!level.isClientSide()) {
            return InteractionResult.SUCCESS;
        }

        BraidSamplesClient.open();
        return InteractionResult.SUCCESS;
    }
}
