package io.wispforest.uwu.items;

import net.fabricmc.api.EnvType;
import net.fabricmc.api.Environment;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.tooltip.TooltipComponent;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Rarity;
import net.minecraft.world.level.Level;

import java.util.Optional;

/**
 * Item that opens the braid display / test selector.
 *
 * <p>All client-only code lives in {@link UwuBraidClient}: this class must stay loadable on a
 * dedicated server. A member of this class that referenced a client-only type would make the JVM
 * resolve that class while the item class is being initialized, which fails on a server with
 * {@code Cannot load class net.minecraft.client.gui.screens.Screen in environment type SERVER}.
 */
public class UwuBraidItem extends Item {

    public UwuBraidItem(Properties settings) {
        super(settings.rarity(Rarity.EPIC));
    }

    @Override
    @Environment(EnvType.CLIENT)
    public InteractionResult use(Level world, Player user, InteractionHand hand) {
        if (world.isClientSide()) {
            if (user.isShiftKeyDown()) {
                UwuBraidClient.openDisplay(user);
            } else {
                UwuBraidClient.openTestSelector();
            }
        }
        return InteractionResult.PASS;
    }

    @Override
    @Environment(EnvType.CLIENT)
    public Optional<TooltipComponent> getTooltipImage(ItemStack stack) {
        return Optional.of(new UwuBraidClient.Tooltip());
    }
}
